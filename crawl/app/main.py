import hmac
import inspect
import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from .streaming import stream_router_sse
from pydantic import BaseModel, Field

from .answering import answer_question
from .agents.traffic_agent import run_traffic_agent
from .agents.labor_agent import run_labor_agent
from .agents.accounting_agent import run_accounting_agent
from .config import get_settings
from .domains import CorpusNotFoundError, UnknownDomainError
from .intent_guardrail import get_intent_guardrail
from .retrieval import get_hybrid_retriever
from .router import run_router
from .query_normalization import clean_query
from .overview import build_domain_overview, detect_overview_domain
from .vectorstore import get_vectorstore, ingest_domain, ingest_labor, search_domain, search_labor
from .provenance import canonical_json, create_receipt, merkle_proof, receipt_db, verify_merkle_proof
from .contributions import ContributionInput, list_contributions, review_contribution, submit_contribution
from .db import (
    ConversationCreate,
    ConversationUpdate,
    add_message,
    create_conversation,
    delete_all_conversations,
    delete_conversation as delete_conversation_record,
    ensure_conversation,
    get_conversation,
    get_conversation_messages,
    list_conversations,
    update_conversation_title,
)

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
        from x402.schemas import AssetAmount
        from x402.server import x402ResourceServer
    except ImportError as exc:
        raise RuntimeError("Install the payments extra: pip install -e '.[payments]'") from exc

    server = x402ResourceServer(
        HTTPFacilitatorClient(FacilitatorConfig(url=settings.x402_facilitator_url))
    )
    server.register(settings.x402_network, ExactEvmServerScheme())
    price: str | AssetAmount = f"${settings.x402_price_usd}"
    if settings.x402_asset_address:
        atomic_amount = Decimal(settings.x402_price_usd) * (Decimal(10) ** settings.x402_asset_decimals)
        if atomic_amount != atomic_amount.to_integral_value():
            raise RuntimeError("X402_PRICE_USD supports fewer decimal places than X402_ASSET_DECIMALS")
        price = AssetAmount(
            amount=str(int(atomic_amount)),
            asset=settings.x402_asset_address,
            extra={"name": settings.x402_asset_name, "version": settings.x402_asset_version},
        )
    app.add_middleware(
        PaymentMiddlewareASGI,
        routes={
            "POST /paid/traffic/ask": RouteConfig(
                accepts=[PaymentOption(
                    scheme="exact",
                    price=price,
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
    "/router/ask/stream",
    "/agents/traffic/ask",
    "/agents/labor/ask",
    "/agents/accounting/ask",
    "/agents/tax/ask",
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
    if not getattr(settings, "require_api_key", False) or not requires_api_key(request.method, request.url.path):
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
    conversation_id: str | None = Field(default=None, description="Conversation persistence ID")
    stream: bool = Field(default=False, description="Bật chế độ Server-Sent Events (SSE) streaming")


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
    request = clean_request(request)
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
    web_url = get_settings().trust_agent_web_url.rstrip("/")
    metadata["services"] = [
        {"name": "web", "endpoint": web_url},
        {"name": "x402", "endpoint": f"{base_url}/paid/traffic/ask", "version": "2"},
    ]
    metadata["x402Support"] = get_settings().x402_enabled
    metadata.pop("supportedTrust", None)
    return metadata


@app.get("/domains/{domain}/health")
def domain_health(domain: str) -> dict[str, Any]:
    settings, config = domain_settings(domain)
    count = collection_document_count(settings, config)
    return {"status": "ok", "domain": config.name, "collection": config.collection_name, "document_count": count}


@app.get("/domains/{domain}/overview")
def domain_overview(domain: str) -> dict[str, Any]:
    settings, config = domain_settings(domain)
    try:
        return build_domain_overview(settings, config)
    except Exception as exc:
        logger.exception("Domain overview failed: %s", config.name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    request = clean_request(request)
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
    request = clean_request(request)
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



@app.post("/api/conversations", status_code=201)
def create_conversation_endpoint(request: ConversationCreate) -> dict[str, Any]:
    return create_conversation(title=request.title)


@app.get("/api/conversations")
def list_conversations_endpoint(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be non-negative")
    return list_conversations(limit=limit, offset=offset)


@app.get("/api/conversations/{conversation_id}")
def get_conversation_endpoint(conversation_id: str) -> dict[str, Any]:
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.get("/api/conversations/{conversation_id}/messages")
def get_conversation_messages_endpoint(conversation_id: str) -> list[dict[str, Any]]:
    if get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return get_conversation_messages(conversation_id)


@app.patch("/api/conversations/{conversation_id}")
def update_conversation_endpoint(conversation_id: str, request: ConversationUpdate) -> dict[str, Any]:
    if get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    updated = update_conversation_title(conversation_id, request.title)
    if updated is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return updated


@app.delete("/api/conversations/{conversation_id}", status_code=204)
def delete_conversation_endpoint(conversation_id: str) -> None:
    if not delete_conversation_record(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return None


@app.delete("/api/conversations", status_code=200)
def delete_all_conversations_endpoint() -> dict[str, Any]:
    """Clear visible conversations and their LangGraph memory."""
    from .checkpoint import get_sqlite_checkpointer

    deleted = delete_all_conversations()
    get_sqlite_checkpointer().delete_all_threads()
    return {"deleted": deleted}

@app.post("/ask")
def ask(request: SearchRequest) -> dict[str, Any]:
    request = clean_request(request)
    try:
        settings = get_settings()
        config = settings.domain_config(settings.labor_domain) if hasattr(settings, "domain_config") else None
        if config is not None and detect_overview_domain(request.query) == config.name:
            overview = build_domain_overview(settings, config)
            return {
                "query": request.query,
                "domain": config.name,
                "answer": overview["answer"],
                "status": overview["status"],
                "citations": [],
                "evidence": [],
                "overview": overview,
                "retrieval_strategy": "metadata_overview",
            }
        return answer_question(request.query, request.k, settings)
    except Exception as exc:
        logger.exception("Labor ask failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/domains/{domain}/ask")
def domain_ask(domain: str, request: SearchRequest) -> dict[str, Any]:
    request = clean_request(request)
    settings, config = domain_settings(domain)
    try:
        if detect_overview_domain(request.query) == config.name:
            overview = build_domain_overview(settings, config)
            return {
                "query": request.query,
                "domain": config.name,
                "answer": overview["answer"],
                "status": overview["status"],
                "citations": [],
                "evidence": [],
                "overview": overview,
                "retrieval_strategy": "metadata_overview",
            }
        return answer_question(request.query, request.k, settings, domain=config.name)
    except Exception as exc:
        logger.exception("Domain ask failed: %s", config.name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/router/ask")
def router_ask(request: SearchRequest) -> Any:
    request = clean_request(request)
    conversation_id = request.conversation_id or request.thread_id or request.session_id
    if request.stream:
        return StreamingResponse(
            stream_router_sse(request.query, request.k, conversation_id),
            media_type="text/event-stream",
        )
    try:
        conversation = ensure_conversation(
            conversation_id=conversation_id,
            default_title=request.query[:255],
        )
        conversation_id = conversation["id"]
        router_parameters = inspect.signature(run_router).parameters
        supports_thread_id = "thread_id" in router_parameters
        router_kwargs: dict[str, Any] = {}
        if supports_thread_id:
            router_kwargs["thread_id"] = conversation_id
        response = run_router(request.query, request.k, **router_kwargs)
        answer = response.get("answer", "")
        add_message(conversation_id, "user", request.query)
        add_message(
            conversation_id,
            "assistant",
            answer,
            citations=response.get("citations", []),
            status=response.get("status"),
            metadata={
                "domain": response.get("domain"),
                "guardrail_status": response.get("guardrail_status"),
            },
        )
        if supports_thread_id:
            response["conversation_id"] = conversation_id
            response["thread_id"] = conversation_id
            response["session_id"] = conversation_id
        return response
    except Exception as exc:
        logger.exception("Router ask failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/router/ask/stream")
def router_ask_stream(request: SearchRequest) -> StreamingResponse:
    request = clean_request(request)
    conversation_id = request.conversation_id or request.thread_id or request.session_id
    return StreamingResponse(
        stream_router_sse(request.query, request.k, conversation_id),
        media_type="text/event-stream",
    )
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
    intent_result = get_intent_guardrail().check_intent(cleaned.query)
    if intent_result.intent != "in_scope":
        return {
            "query": cleaned.query,
            "answer": intent_result.response or "Hãy nhập câu hỏi pháp luật cụ thể.",
            "status": intent_result.intent,
            "citations": [],
            "payment": {"scheme": "x402", "network": get_settings().x402_network},
        }
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


@app.post("/paid/traffic/validate")
def validate_paid_traffic(request: SearchRequest) -> dict[str, Any]:
    """Validate a paid query before the browser requests an x402 payment challenge."""
    cleaned = clean_request(request)
    intent_result = get_intent_guardrail().check_intent(cleaned.query)
    return {
        "allowed": intent_result.intent == "in_scope",
        "query": cleaned.query,
        "status": intent_result.intent,
        "answer": intent_result.response,
    }


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
@app.post("/agents/tax/ask")
def accounting_agent_ask(request: SearchRequest) -> dict[str, Any]:
    try:
        cleaned = clean_request(request)
        return run_accounting_agent(cleaned.query, cleaned.k)
    except Exception as exc:
        logger.exception("Accounting agent ask failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
