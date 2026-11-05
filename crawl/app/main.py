import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .answering import answer_question
from .config import get_settings
from .domains import CorpusNotFoundError, UnknownDomainError
from .retrieval import get_hybrid_retriever
from .vectorstore import get_vectorstore, ingest_domain, ingest_labor, search_domain, search_labor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
app = FastAPI(title="Trust Agent Multi-Domain RAG", version="0.2.0")


class IngestRequest(BaseModel):
    force: bool = False


class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    k: int = Field(default=5, ge=1, le=20)


def citation(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: metadata.get(key) for key in ("ten_van_ban", "so_hieu", "dieu", "khoan", "source")}


def public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    result = dict(metadata)
    if result.get("effective_from") == "":
        result["effective_from"] = None
    return result


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
    try:
        count = get_vectorstore(settings, config.name)._collection.count()
    except Exception:
        count = 0
    return {"status": "ok", "domain": config.name, "collection": config.collection_name, "document_count": count}


@app.get("/domains/{domain}/health")
def domain_health(domain: str) -> dict[str, Any]:
    settings, config = domain_settings(domain)
    try:
        count = get_vectorstore(settings, config.name)._collection.count()
    except Exception:
        count = 0
    return {"status": "ok", "domain": config.name, "collection": config.collection_name, "document_count": count}


@app.post("/ingest")
def ingest(request: IngestRequest | None = None) -> dict[str, Any]:
    try:
        result = ingest_labor(get_settings())
        return {"status": "ok", "domain": get_settings().labor_domain, **result.__dict__}
    except Exception as exc:
        logger.exception("Labor ingest failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/domains/{domain}/ingest")
def ingest_domain_endpoint(domain: str, request: IngestRequest | None = None) -> dict[str, Any]:
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