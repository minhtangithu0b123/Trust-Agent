import hmac
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .answering import answer_question
from .agents.traffic_agent import run_traffic_agent
from .agents.labor_agent import run_labor_agent
from .agents.accounting_agent import run_accounting_agent
from .config import get_settings
from .domains import CorpusNotFoundError, UnknownDomainError
from .retrieval import get_hybrid_retriever
from .router import run_router
from .query_normalization import clean_query
from .vectorstore import get_vectorstore, ingest_domain, ingest_labor, search_domain, search_labor
from .provenance import canonical_json, create_receipt, merkle_proof, receipt_db, verify_merkle_proof
from .contributions import ContributionInput, list_contributions, review_contribution, submit_contribution

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
app = FastAPI(title="Trust Agent Multi-Domain RAG", version="0.2.0")


def configure_x402() -> None:
    settings = get_settings()
    if not settings.x402_enabled:
        return
    if not settings.x402_pay_to or not settings.x402_facilitator_url:
        raise RuntimeError("X402_PAY_TO and X402_FACILITATOR_URL are required when X402_ENABLED=true")
    try:
        from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
        from x402.http.middleware.fastapi import PaymentMiddlewareASGI
        from x402.http.types import RouteConfig
        from x402.mechanisms.evm.exact import ExactEvmServerScheme
        from x402.server import x402ResourceServer
    except ImportError as exc:
        raise RuntimeError("Install the payments extra: pip install -e '.[payments]'") from exc

    server = x402ResourceServer(
        HTTPFacilitatorClient(FacilitatorConfig(url=settings.x402_facilitator_url))
    )
    server.register(settings.x402_network, ExactEvmServerScheme())
    app.add_middleware(
        PaymentMiddlewareASGI,
        routes={
            "POST /paid/traffic/ask": RouteConfig(
                accepts=[PaymentOption(
                    scheme="exact",
                    price=f"${settings.x402_price_usd}",
                    network=settings.x402_network,
                    pay_to=settings.x402_pay_to,
                )],
                description="Vietnamese traffic-law answer with citations",
            )
        },
        server=server,
    )


configure_x402()


_QUERY_API_PATHS = {
    "/ask",
    "/search",
    "/search/hybrid",
    "/router/ask",
    "/agents/traffic/ask",
    "/agents/labor/ask",
    "/agents/accounting/ask",
}


def requires_api_key(method: str, path: str) -> bool:
    if method != "POST":
        return False
    if path in _QUERY_API_PATHS:
        return True
    if not path.startswith("/domains/"):
        return False
    return path.endswith(("/ask", "/search", "/search/hybrid"))


@app.middleware("http")
async def protect_query_api(request: Request, call_next):
    settings = get_settings()
    if not settings.require_api_key or not requires_api_key(request.method, request.url.path):
        return await call_next(request)
    expected = settings.api_access_token
    if not expected:
        return JSONResponse({"detail": "API access is not configured"}, status_code=503)
    supplied = request.headers.get("X-API-Key", "")
    if not hmac.compare_digest(supplied, expected):
        return JSONResponse({"detail": "API key required"}, status_code=401)
    return await call_next(request)


class IngestRequest(BaseModel):
    force: bool = False


class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    k: int = Field(default=5, ge=1, le=20)
    thread_id: str | None = Field(default=None, description="Thread ID cho phiên hội thoại đa lượt")
    session_id: str | None = Field(default=None, description="Tương đương thread_id")


class ContributionReview(BaseModel):
    approve: bool


def clean_request(request: SearchRequest) -> SearchRequest:
    return request.model_copy(update={"query": clean_query(request.query)})


def citation(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: metadata.get(key) for key in ("ten_van_ban", "so_hieu", "dieu", "khoan", "source")}


def public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    result = dict(metadata)
    if result.get("effective_from") == "":
        result["effective_from"] = None
    return result


def require_ingest_admin(token: str | None) -> None:
    expected = get_settings().ingest_admin_token
    if not expected:
        raise HTTPException(status_code=503, detail="Ingestion API is disabled")
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Ingestion authorization required")


def collection_document_count(settings, config) -> int:
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(settings.chroma_path))
        return client.get_collection(name=config.collection_name).count()
    except Exception as exc:
        logger.warning("Health check could not read collection %s: %s", config.collection_name, exc)
        return 0


def domain_settings(domain: str):
    settings = get_settings()
    try:
        config = settings.domain_config(domain)
    except UnknownDomainError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return settings, config


def hybrid_response(settings, config, request: SearchRequest) -> dict[str, Any]:
    results = get_hybrid_retriever(settings, domain=config.name).search(request.query, request.k)
    return {
        "query": request.query,
        "domain": config.name,
        "strategy": "hybrid_rrf",
        "results": [
            {
                "text": result.document.page_content,
                "fused_score": result.fused_score,
                "metadata": public_metadata(result.document.metadata),
                "citation": {
                    key: result.document.metadata.get(key)
                    for key in ("ten_van_ban", "so_hieu", "chuong", "dieu", "khoan", "source")
                },
            }
            for result in results
        ],
    }


@app.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    config = settings.domain_config(settings.labor_domain)
    count = collection_document_count(settings, config)
    return {"status": "ok", "domain": config.name, "collection": config.collection_name, "document_count": count}


@app.get("/agent-registration.json")
def agent_registration(request: Request) -> dict[str, Any]:
    """Serve ERC-8004 metadata from the same public host as the API."""
    metadata_path = Path(__file__).with_name("agent-registration.example.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    base_url = str(request.base_url).rstrip("/")
    metadata["services"] = [
        {"name": "web", "endpoint": f"{base_url}/docs"},
        {"name": "x402", "endpoint": f"{base_url}/paid/traffic/ask", "version": "2"},
    ]
    metadata["x402Support"] = get_settings().x402_enabled
    return metadata


@app.get("/domains/{domain}/health")
def domain_health(domain: str) -> dict[str, Any]:
    settings, config = domain_settings(domain)
    count = collection_document_count(settings, config)
    return {"status": "ok", "domain": config.name, "collection": config.collection_name, "document_count": count}


@app.post("/ingest")
def ingest(
    request: IngestRequest | None = None,
    x_ingest_token: str | None = Header(default=None, alias="X-Ingest-Token"),
) -> dict[str, Any]:
    require_ingest_admin(x_ingest_token)
    try:
        result = ingest_labor(get_settings())
        return {"status": "ok", "domain": get_settings().labor_domain, **result.__dict__}
    except Exception as exc:
        logger.exception("Labor ingest failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/domains/{domain}/ingest")
def ingest_domain_endpoint(
    domain: str,
    request: IngestRequest | None = None,
    x_ingest_token: str | None = Header(default=None, alias="X-Ingest-Token"),
) -> dict[str, Any]:
    require_ingest_admin(x_ingest_token)
    settings, config = domain_settings(domain)
    try:
        result = ingest_domain(settings, config.name)
        return {"status": "ok", "domain": config.name, "collection": config.collection_name, **result.__dict__}
    except CorpusNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Domain ingest failed: %s", config.name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/search")
def search(request: SearchRequest) -> dict[str, Any]:
    try:
        documents = search_labor(get_settings(), request.query, request.k)
        return {"query": request.query, "results": [
            {"content": document.page_content, "metadata": public_metadata(document.metadata), "citation": citation(document.metadata)}
            for document in documents
        ]}
    except Exception as exc:
        logger.exception("Labor search failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/domains/{domain}/search")
def domain_search(domain: str, request: SearchRequest) -> dict[str, Any]:
    settings, config = domain_settings(domain)
    try:
        documents = search_domain(settings, config.name, request.query, request.k)
        return {
            "query": request.query,
            "domain": config.name,
            "results": [
                {
                    "content": document.page_content,
                    "metadata": public_metadata(document.metadata),
                    "citation": {
                        key: document.metadata.get(key)
                        for key in ("ten_van_ban", "so_hieu", "chuong", "dieu", "khoan", "source")
                    },
                }
                for document in documents
            ],
        }
    except Exception as exc:
        logger.exception("Domain search failed: %s", config.name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/search/hybrid")
def hybrid_search(request: SearchRequest) -> dict[str, Any]:
    try:
        settings = get_settings()
        config = settings.domain_config(settings.labor_domain)
        response = hybrid_response(settings, config, request)
        response.pop("domain", None)
        return response
    except Exception as exc:
        logger.exception("Labor hybrid search failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/domains/{domain}/search/hybrid")
def domain_hybrid_search(domain: str, request: SearchRequest) -> dict[str, Any]:
    settings, config = domain_settings(domain)
    try:
        return hybrid_response(settings, config, request)
    except Exception as exc:
        logger.exception("Domain hybrid search failed: %s", config.name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ask")
def ask(request: SearchRequest) -> dict[str, Any]:
    try:
        return answer_question(request.query, request.k, get_settings())
    except Exception as exc:
        logger.exception("Labor ask failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/domains/{domain}/ask")
def domain_ask(domain: str, request: SearchRequest) -> dict[str, Any]:
    settings, config = domain_settings(domain)
    try:
        return answer_question(request.query, request.k, settings, domain=config.name)
    except Exception as exc:
        logger.exception("Domain ask failed: %s", config.name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/router/ask")
def router_ask(request: SearchRequest) -> dict[str, Any]:
    try:
        thread_id = request.thread_id or request.session_id
        if thread_id is not None:
            response = run_router(request.query, request.k, thread_id=thread_id)
        else:
            response = run_router(request.query, request.k)
        if isinstance(response, dict):
            if "thread_id" not in response and thread_id is not None:
                response["thread_id"] = thread_id
            if request.session_id is not None and "session_id" not in response:
                response["session_id"] = request.session_id
        return response
    except Exception as exc:
        logger.exception("Router ask failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
@app.post("/agents/traffic/ask")
def traffic_agent_ask(request: SearchRequest) -> dict[str, Any]:
    try:
        cleaned = clean_request(request)
        return run_traffic_agent(cleaned.query, cleaned.k)
    except Exception as exc:
        logger.exception("Traffic agent ask failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/paid/traffic/ask")
def paid_traffic_agent_ask(request: SearchRequest) -> dict[str, Any]:
    if not get_settings().x402_enabled:
        raise HTTPException(status_code=503, detail="Paid API is not enabled")
    cleaned = clean_request(request)
    result = run_traffic_agent(cleaned.query, cleaned.k)
    receipt = create_receipt(result["answer"], result.get("citations", []), get_settings().index_version)
    result["provenance"] = {
        "receipt_id": receipt["receipt_id"],
        "receipt_hash": receipt["leaf_hash"],
        "index_version": receipt["index_version"],
    }
    result["payment"] = {
        "scheme": "x402",
        "network": get_settings().x402_network,
    }
    return result


@app.get("/provenance/{receipt_id}")
def get_provenance(receipt_id: str) -> dict[str, Any]:
    import hashlib
    import sqlite3

    path = receipt_db()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Receipt not found")
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT r.payload, r.leaf_hash, r.batch_root, b.tx_hash, b.chain_id, b.status "
            "FROM receipts r LEFT JOIN batches b ON b.root = r.batch_root WHERE r.receipt_id = ?",
            (receipt_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    import json

    receipt = json.loads(row[0])
    proof = []
    if row[2]:
        with sqlite3.connect(path) as connection:
            leaves = [item[0] for item in connection.execute(
                "SELECT leaf_hash FROM receipts WHERE batch_root = ? ORDER BY created_at, receipt_id", (row[2],)
            )]
            index = next(i for i, leaf in enumerate(leaves) if leaf == row[1])
        proof = merkle_proof(leaves, index)
    verified = verify_merkle_proof(row[1], proof, row[2]) if row[2] else False
    verified = verified and hashlib.sha256(canonical_json(receipt)).hexdigest() == row[1]
    return {
        "receipt": receipt,
        "leaf_hash": row[1],
        "batch_root": row[2],
        "proof": proof,
        "proof_valid": verified,
        "anchor": {"status": row[5], "tx_hash": row[3], "chain_id": row[4]},
    }


@app.post("/contributions", status_code=202)
def create_contribution(request: ContributionInput) -> dict[str, str]:
    return submit_contribution(request)


@app.get("/admin/contributions")
def admin_contributions(x_review_token: str | None = Header(default=None, alias="X-Review-Token")) -> list[dict]:
    return list_contributions(x_review_token)


@app.post("/admin/contributions/{contribution_id}/review")
def admin_review_contribution(
    contribution_id: str,
    request: ContributionReview,
    x_review_token: str | None = Header(default=None, alias="X-Review-Token"),
) -> dict:
    return review_contribution(contribution_id, request.approve, x_review_token)
@app.post("/agents/labor/ask")
def labor_agent_ask(request: SearchRequest) -> dict[str, Any]:
    try:
        cleaned = clean_request(request)
        return run_labor_agent(cleaned.query, cleaned.k)
    except Exception as exc:
        logger.exception("Labor agent ask failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/agents/accounting/ask")
def accounting_agent_ask(request: SearchRequest) -> dict[str, Any]:
    try:
        cleaned = clean_request(request)
        return run_accounting_agent(cleaned.query, cleaned.k)
    except Exception as exc:
        logger.exception("Accounting agent ask failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
