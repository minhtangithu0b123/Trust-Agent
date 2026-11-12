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
    updated: int
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


def ingest_domain(settings: Settings, domain: str, force: bool = False) -> IngestResult:
    config = settings.domain_config(domain)
    data_path = settings.resolve_path(config.data_path)
    if not data_path.exists():
        raise CorpusNotFoundError(
            f"Corpus for domain '{config.name}' not found: {data_path}. "
            "Add the corpus or update app/domains.py before ingesting."
        )
    pairs = load_documents(data_path, config)
    store = get_vectorstore(settings, config.name)
    payload = store.get(
        where={"domain": config.name},
        include=["documents", "metadatas"],
    )
    existing = {
        record_id: (text or "", metadata or {})
        for record_id, text, metadata in zip(
            payload.get("ids", []),
            payload.get("documents", []),
            payload.get("metadatas", []),
        )
    }

    added: list[tuple[str, object]] = []
    updated: list[tuple[str, object]] = []
    skipped = 0
    for record_id, document in pairs:
        current = existing.get(record_id)
        if current is None:
            added.append((record_id, document))
        elif current[0] != document.page_content or current[1] != document.metadata:
            updated.append((record_id, document))
        else:
            skipped += 1

    if added:
        store.add_documents(
            documents=[document for _, document in added],
            ids=[record_id for record_id, _ in added],
        )
    if updated:
        store.update_documents(
            ids=[record_id for record_id, _ in updated],
            documents=[document for _, document in updated],
        )
    if force:
        # Delete stale IDs only after all source records were added/updated, so
        # a failed re-embed does not first empty the live domain index.
        source_ids = {record_id for record_id, _ in pairs}
        stale_ids = [record_id for record_id in existing if record_id not in source_ids]
        if stale_ids:
            store.delete(ids=stale_ids)
    if force or added or updated:
        # The collection count alone cannot detect metadata/content updates.
        from .retrieval import invalidate_hybrid_retriever

        invalidate_hybrid_retriever(settings, config.name)
    count = store._collection.count()
    logger.info(
        "Domain ingest: domain=%s total=%s added=%s updated=%s skipped=%s force=%s collection=%s count=%s",
        config.name, len(pairs), len(added), len(updated), skipped, force, config.collection_name, count,
    )
    return IngestResult(len(pairs), len(added), len(updated), skipped, count)


def search_domain(settings: Settings, domain: str, query: str, k: int = 5):
    config = settings.domain_config(domain)
    store = get_vectorstore(settings, config.name)
    return store.similarity_search(query, k=k, filter={"domain": config.name})


# Backward-compatible Labor helpers.
def ingest_labor(settings: Settings, force: bool = False) -> IngestResult:
    return ingest_domain(settings, settings.labor_domain, force=force)


def search_labor(settings: Settings, query: str, k: int = 5):
    return search_domain(settings, settings.labor_domain, query, k)
