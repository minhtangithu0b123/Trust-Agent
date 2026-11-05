import logging
from dataclasses import dataclass
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from .config import Settings
from .domains import CorpusNotFoundError
from .normalization import load_documents

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    total: int
    added: int
    skipped_existing: int
    collection_count: int


@lru_cache(maxsize=4)
def build_embeddings(model_name: str, device: str) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_vectorstore(settings: Settings, domain: str = "labor") -> Chroma:
    config = settings.domain_config(domain)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=config.collection_name,
        persist_directory=str(settings.chroma_path),
        embedding_function=build_embeddings(settings.embedding_model, settings.embedding_device),
    )


def ingest_domain(settings: Settings, domain: str) -> IngestResult:
    config = settings.domain_config(domain)
    data_path = settings.resolve_path(config.data_path)
    if not data_path.exists():
        raise CorpusNotFoundError(
            f"Corpus for domain '{config.name}' not found: {data_path}. "
            "Add the corpus or update app/domains.py before ingesting."
        )
    pairs = load_documents(data_path, config)
    store = get_vectorstore(settings, config.name)
    existing = set(store.get(include=[]).get("ids", []))
    pending = [(record_id, document) for record_id, document in pairs if record_id not in existing]
    if pending:
        store.add_documents(
            documents=[document for _, document in pending],
            ids=[record_id for record_id, _ in pending],
        )
    count = store._collection.count()
    logger.info(
        "Domain ingest: domain=%s total=%s added=%s skipped=%s collection=%s count=%s",
        config.name, len(pairs), len(pending), len(pairs) - len(pending), config.collection_name, count,
    )
    return IngestResult(len(pairs), len(pending), len(pairs) - len(pending), count)


def search_domain(settings: Settings, domain: str, query: str, k: int = 5):
    config = settings.domain_config(domain)
    store = get_vectorstore(settings, config.name)
    return store.similarity_search(query, k=k, filter={"domain": config.name})


# Backward-compatible Labor helpers.
def ingest_labor(settings: Settings) -> IngestResult:
    return ingest_domain(settings, settings.labor_domain)


def search_labor(settings: Settings, query: str, k: int = 5):
    return search_domain(settings, settings.labor_domain, query, k)