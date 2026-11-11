import logging
import re
from dataclasses import dataclass
from typing import Iterable

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from .config import Settings
from .vectorstore import get_vectorstore

logger = logging.getLogger(__name__)
TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


def rrf_fuse(rankings: Iterable[Iterable[str]], rrf_k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        seen: set[str] = set()
        for rank, item_id in enumerate(ranking, start=1):
            if item_id in seen:
                continue
            seen.add(item_id)
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (rrf_k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


@dataclass
class HybridResult:
    document: Document
    fused_score: float


class HybridRetriever:
    def __init__(self, settings: Settings, domain: str = "labor"):
        self.settings = settings
        self.domain = settings.domain_config(domain).name
        self.store = get_vectorstore(settings, self.domain)
        self._collection_count = -1
        self._documents: dict[str, Document] = {}
        self._bm25: BM25Okapi | None = None
        self.refresh_if_needed()

    def refresh_if_needed(self) -> None:
        count = self.store._collection.count()
        if count != self._collection_count:
            self.refresh()

    def refresh(self) -> None:
        payload = self.store.get(include=["documents", "metadatas"])
        documents: dict[str, Document] = {}
        for item_id, text, metadata in zip(
            payload.get("ids", []), payload.get("documents", []), payload.get("metadatas", [])
        ):
            metadata = metadata or {}
            if metadata.get("domain") == self.domain:
                documents[item_id] = Document(page_content=text or "", metadata=metadata)
        self._documents = documents
        self._bm25 = BM25Okapi([tokenize(doc.page_content) for doc in documents.values()]) if documents else None
        self._collection_count = self.store._collection.count()
        logger.info("BM25 index refreshed: domain=%s documents=%s", self.domain, len(documents))

    def _sparse_ids(self, query: str, limit: int) -> list[str]:
        if not self._bm25 or not self._documents:
            return []
        ids = list(self._documents)
        scores = self._bm25.get_scores(tokenize(query))
        # BM25 returns a score for every document. Returning the top ``limit``
        # even when every score is zero makes unrelated documents look like
        # lexical matches and pollutes the reciprocal-rank fusion results.
        ranked = sorted(
            (index for index, score in enumerate(scores) if score > 0),
            key=lambda index: (-scores[index], ids[index]),
        )
        return [ids[index] for index in ranked[:limit]]

    def search(self, query: str, k: int = 5, candidate_k: int | None = None) -> list[HybridResult]:
        self.refresh_if_needed()
        candidate_k = candidate_k or max(k * 4, 20)
        dense_docs = self.store.similarity_search(query, k=candidate_k, filter={"domain": self.domain})
        dense_by_id = {doc.metadata.get("id"): doc for doc in dense_docs if doc.metadata.get("id")}
        fused = rrf_fuse([list(dense_by_id), self._sparse_ids(query, candidate_k)])[:k]
        return [
            HybridResult(dense_by_id.get(item_id) or self._documents[item_id], score)
            for item_id, score in fused
            if item_id in dense_by_id or item_id in self._documents
        ]


_RETRIEVERS: dict[tuple[str, str, str, str], HybridRetriever] = {}


def get_hybrid_retriever(settings: Settings, domain: str = "labor") -> HybridRetriever:
    config = settings.domain_config(domain)
    key = (str(settings.chroma_path), config.collection_name, settings.embedding_model, config.name)
    if key not in _RETRIEVERS:
        _RETRIEVERS[key] = HybridRetriever(settings, domain=config.name)
    return _RETRIEVERS[key]


def invalidate_hybrid_retriever(settings: Settings, domain: str) -> None:
    """Drop cached BM25 state after documents are added or updated in Chroma."""
    config = settings.domain_config(domain)
    key = (str(settings.chroma_path), config.collection_name, settings.embedding_model, config.name)
    _RETRIEVERS.pop(key, None)
