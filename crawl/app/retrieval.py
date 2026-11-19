import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from .config import Settings
from .query_normalization import clean_query, expand_query_for_retrieval, normalize_for_routing
from .vectorstore import get_vectorstore
from .self_query import QueryPlan, build_query_plan
from .reranker import rerank
from .query_facets import facet_score
from .query_complexity import assess_query_complexity

logger = logging.getLogger(__name__)
TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


def _original_span_for_routing_match(text: str, start: int, end: int) -> tuple[int, int]:
    """Map an accent-folded routing span back to the cleaned source text.

    ``normalize_for_routing`` removes combining marks and folds ``đ``.  Its
    offsets therefore cannot safely be used to slice the original text.
    Build an offset table while applying the same per-character folding so
    traffic point-deduction branches retain the correct Vietnamese text.
    """
    cleaned = clean_query(text)
    folded_chars: list[str] = []
    source_offsets: list[int] = []
    for source_index, character in enumerate(cleaned.casefold()):
        decomposed = unicodedata.normalize("NFD", character)
        folded = "".join(
            item for item in decomposed
            if unicodedata.category(item) != "Mn"
        ).replace("đ", "d")
        for item in folded:
            folded_chars.append(item)
            source_offsets.append(source_index)
    folded_text = "".join(folded_chars)
    # The routing normalizer also collapses whitespace. Legal chunks are
    # normally already clean, but use a bounded fallback if whitespace makes
    # the two representations differ.
    if folded_text != normalize_for_routing(cleaned):
        return start, end
    if not source_offsets or start >= len(source_offsets):
        return start, end
    source_start = source_offsets[max(0, start)]
    source_end = source_offsets[min(len(source_offsets) - 1, max(start, end - 1))] + 1
    return source_start, source_end
def tokenize(text: str) -> list[str]:
    # Keep legal Vietnamese terms accent-sensitive for BM25 precision.
    # Unaccented queries are handled by query expansion and dense retrieval.
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
        bm25_texts = [
            " ".join(
                str(doc.metadata.get(field, ""))
                for field in ("ten_van_ban", "chuong", "dieu", "tieu_de_dieu", "khoan")
            )
            + " "
            + doc.page_content
            for doc in documents.values()
        ]
        self._bm25 = BM25Okapi([tokenize(text) for text in bm25_texts]) if documents else None
        self._collection_count = self.store._collection.count()
        logger.info("BM25 index refreshed: domain=%s documents=%s", self.domain, len(documents))

    @staticmethod
    def _matches_metadata_filter(document: Document, metadata_filter: dict[str, object]) -> bool:
        metadata = document.metadata or {}
        for key, expected in metadata_filter.items():
            actual = str(metadata.get(key, ""))
            normalize = lambda value: re.sub(r"\s+", " ", value.casefold()).strip()
            def matches(value: object) -> bool:
                expected_text = normalize(str(value))
                actual_text = normalize(actual)
                if key in {"traffic_topics", "topic_tags"}:
                    return expected_text in {
                        token.strip() for token in actual_text.split("|") if token.strip()
                    }
                if key in {"dieu", "khoan"}:
                    return actual_text == expected_text or actual_text.startswith(expected_text + " ") or actual_text.startswith(expected_text + ".")
                return actual_text == expected_text
            if isinstance(expected, (list, tuple, set)):
                if not any(matches(value) for value in expected):
                    return False
            elif not matches(expected):
                return False
        return True

    def _sparse_ids(
        self,
        query: str,
        limit: int,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[str]:
        if not self._bm25 or not self._documents:
            return []
        metadata_filter = metadata_filter or {"domain": self.domain}
        ids = [
            item_id
            for item_id, document in self._documents.items()
            if self._matches_metadata_filter(document, metadata_filter)
        ]
        if not ids:
            return []
        positions = {item_id: index for index, item_id in enumerate(self._documents)}
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(
            ids,
            key=lambda item_id: (-scores[positions[item_id]], item_id),
        )
        return ranked[:limit]

    def _expand_parent_context(
        self,
        results: list[HybridResult],
        query: str = "",
    ) -> list[HybridResult]:
        """Attach nearby clauses from the same legal article to each hit.

        Chroma/BM25 continue ranking small clause-level children. The returned
        result keeps the winning child id for citation verification while its
        text includes a bounded parent article context for the answer model.
        """
        expanded: list[HybridResult] = []

        def traffic_point_excerpt(text: str, article: str, clause: str) -> str:
            """Keep only the point branch matching the queried red-light offence."""
            routing_query = normalize_for_routing(query)
            asks_points = "tru diem" in routing_query or ("tru" in routing_query and "diem" in routing_query)
            asks_red_light = "vuot den do" in routing_query or "den tin hieu" in routing_query
            if self.domain != "traffic" or not asks_red_light or not asks_points:
                return text
            article_key = normalize_for_routing(article)
            clause_key = normalize_for_routing(clause)
            point_key = ""
            clause_ref = ""
            if "dieu 6" in article_key and "khoan 9" in clause_key:
                point_key, clause_ref = "b", "9"
            elif "dieu 7" in article_key and "khoan 7" in clause_key:
                point_key, clause_ref = "c", "7"
            if not point_key:
                return text

            normalized_text = normalize_for_routing(text)
            match = re.search(
                rf"b\)\s+thuc\s+hien.*?diem\s+{point_key}.*?"
                rf"khoan\s+{clause_ref}.*?"
                r"bi\s+tru\s+diem.*?04\s+diem",
                normalized_text,
                flags=re.IGNORECASE,
            )
            if not match:
                match = re.search(
                    rf"diem\s+{point_key}.*?khoan\s+{clause_ref}.*?"
                    r"bi\s+tru\s+diem.*?04\s+diem",
                    normalized_text,
                    flags=re.IGNORECASE,
                )
            if not match:
                return text

            start, end = _original_span_for_routing_match(text, match.start(), match.end())
            cleaned_text = clean_query(text)
            selected_branch = cleaned_text[start:end]
            # Preserve the penalty clause before the point table, then append
            # only the branch that maps the red-light offence to 04 points.
            prefix = cleaned_text[:start].rstrip(" ;")
            return f"{prefix}; {selected_branch}" if prefix else selected_branch

        for result in results:
            metadata = result.document.metadata or {}
            source = str(metadata.get("so_hieu", ""))
            article = str(metadata.get("dieu", ""))
            source_uri = str(metadata.get("source", ""))
            if not source or not article:
                expanded.append(result)
                continue

            siblings = [
                document
                for document in self._documents.values()
                if document.metadata.get("domain") == self.domain
                and str(document.metadata.get("so_hieu", "")) == source
                and str(document.metadata.get("dieu", "")) == article
                and (
                    not source_uri
                    or str(document.metadata.get("source", "")) == source_uri
                )
            ]
            child_id = str(metadata.get("id", ""))
            child_clause = str(metadata.get("khoan", "")).casefold().strip()

            # Keep one child per clause and discard article-title fragments.
            # Most importantly, the ranked child must always remain first;
            # replacing it with the first clauses of an article can turn a
            # correct Khoan 9 hit into an incorrect Khoan 1 answer.
            sibling_by_clause: dict[str, Document] = {}
            for sibling in siblings:
                sibling_id = str(sibling.metadata.get("id", ""))
                clause = str(sibling.metadata.get("khoan", "")).casefold().strip()
                if sibling_id == child_id or clause == child_clause:
                    continue
                if "toàn văn" in clause or "toan van" in clause:
                    continue
                sibling_by_clause.setdefault(clause or sibling_id, sibling)

            related = list(sibling_by_clause.values())
            routing_query = normalize_for_routing(query)
            target_topic = str(metadata.get("traffic_topics", "")).strip()
            if self.domain == "traffic" and target_topic:
                # Do not reintroduce another offence from the same article
                # (for example helmet evidence in a passenger query).
                related = [
                    document for document in related
                    if target_topic in {
                        token.strip()
                        for token in str(document.metadata.get("traffic_topics", "")).split("|")
                        if token.strip()
                    }
                ]
            selected_is_penalty = "phạt tiền" in result.document.page_content.casefold()
            if selected_is_penalty:
                # A penalty clause already contains the applicable fine. Other
                # penalty clauses from the same article describe different
                # offences and their amounts can mislead the answer model.
                # Keep non-penalty siblings such as licence-point deductions
                # and supplementary sanctions when they are relevant.
                related = [
                    document
                    for document in related
                    if "phạt tiền" not in document.page_content.casefold()
                ]
            if related and query.strip():
                corpus = [
                    tokenize(
                        " ".join(
                            str(document.metadata.get(field, ""))
                            for field in ("khoan", "tieu_de_dieu")
                        )
                        + " "
                        + document.page_content
                    )
                    for document in related
                ]
                sibling_scores = BM25Okapi(corpus).get_scores(tokenize(query))

                def context_bonus(document: Document) -> int:
                    text = normalize_for_routing(document.page_content)
                    bonus = 0
                    if "tru diem" in routing_query and "tru diem" in text:
                        bonus += 100
                    if "xu phat bo sung" in routing_query and "xu phat bo sung" in text:
                        bonus += 100
                    if "tuoc quyen su dung giay phep lai xe" in routing_query and "tuoc quyen su dung giay phep lai xe" in text:
                        bonus += 100
                    return bonus

                related = [
                    document
                    for _, document in sorted(
                        ((float(score) + context_bonus(document), document) for score, document in zip(sibling_scores, related)),
                        key=lambda item: (
                            -item[0],
                            str(item[1].metadata.get("id", "")),
                        ),
                    )
                ]
            else:
                related.sort(key=lambda document: str(document.metadata.get("id", "")))

            # Consequence clauses directly answer common follow-up parts of a
            # legal question. Put them immediately after the selected offence
            # instead of allowing generic sibling clauses to consume the
            # limited parent-context budget.
            priority_related = [
                document
                for document in related
                if (
                    "tru diem" in routing_query
                    and "tru diem" in normalize_for_routing(document.page_content)
                )
                or (
                    "xu phat bo sung" in routing_query
                    and "xu phat bo sung" in normalize_for_routing(document.page_content)
                )
            ]
            priority_ids = {str(document.metadata.get("id", "")) for document in priority_related}
            related = [
                *priority_related,
                *[
                    document
                    for document in related
                    if str(document.metadata.get("id", "")) not in priority_ids
                ],
            ]

            ordered_documents = [result.document, *related[:7]]
            # Keep parent context bounded. A citation still points to the
            # retrieved child, while sibling clauses provide conditions and
            # exceptions from the same Article.
            blocks: list[str] = []
            total_chars = 0
            context_changed = False
            for index, sibling in enumerate(ordered_documents):
                clause = str(sibling.metadata.get("khoan", "")).strip()
                text = sibling.page_content.strip()
                original_text = text
                asks_points = "tru diem" in routing_query or ("tru" in routing_query and "diem" in routing_query)
                asks_red_light = "vuot den do" in routing_query or "den tin hieu" in routing_query
                if index >= 0 and asks_red_light and asks_points:
                    # Point-deduction branches contain multiple semicolon-
                    # separated items. Select the branch that maps the
                    # offence itself to 04 points:
                    # cars: point b of Clause 9; motorcycles: point c of
                    # Clause 7. Do not expose the unrelated 06/10 branches.
                    article_key = normalize_for_routing(article)
                    clause_key = normalize_for_routing(child_clause)
                    point_key = ""
                    clause_ref = ""
                    if "dieu 6" in article_key and "khoan 9" in clause_key:
                        point_key, clause_ref = "b", "9"
                    elif "dieu 7" in article_key and "khoan 7" in clause_key:
                        point_key, clause_ref = "c", "7"
                    if point_key:
                        text = traffic_point_excerpt(text, article, child_clause)
                if text != original_text:
                    context_changed = True
                block = f"{clause}: {text}" if clause else text
                if not block:
                    continue
                if index > 0 and total_chars + len(block) > 7000:
                    continue
                blocks.append(block)
                total_chars += len(block)
            if len(blocks) > 1 or context_changed:
                merged_metadata = dict(metadata)
                merged_metadata["parent_id"] = f"{source}:{article}"
                expanded.append(
                    HybridResult(
                        Document(
                            page_content=f"{article} - {metadata.get('tieu_de_dieu', '')}\n" + "\n".join(blocks),
                            metadata=merged_metadata,
                        ),
                        result.fused_score,
                    )
                )
            else:
                expanded.append(result)
        return expanded

    def search(
        self,
        query: str,
        k: int = 5,
        candidate_k: int | None = None,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[HybridResult]:
        self.refresh_if_needed()
        candidate_k = candidate_k or (
            max(k * 4, getattr(self.settings, "reranker_candidate_k", 20))
            if getattr(self.settings, "reranker_enabled", False)
            else max(k * 8, 40)
        )
        retrieval_query = expand_query_for_retrieval(
            query,
            normalize_for_routing(query),
            self.domain,
        )
        # Build metadata constraints from the user's original query. Query
        # expansion may add synonyms for another vehicle class (for example
        # "xe mô tô, xe gắn máy"), which must never cancel an explicit
        # vehicle constraint in the original question.
        plan = (
            build_query_plan(query, self.domain)
            if metadata_filter is None
            else QueryPlan(
                semantic_query=retrieval_query,
                metadata_filter={**metadata_filter, "domain": self.domain},
            )
        )
        # Keep old indexes usable during a rolling ingest. New indexes carry
        # traffic_violation; old ones do not, so temporarily use the normal
        # vehicle/article filters until metadata is refreshed.
        if "traffic_topics" in plan.metadata_filter and not any(
            document.metadata.get("traffic_topics") for document in self._documents.values()
        ):
            plan = QueryPlan(
                semantic_query=plan.semantic_query,
                metadata_filter={
                    key: value
                    for key, value in plan.metadata_filter.items()
                    if key != "traffic_topics"
                },
            )
        dense_docs = self.store.similarity_search(
            plan.semantic_query,
            k=candidate_k,
            filter={"domain": self.domain},
        )
        dense_by_id = {
            doc.metadata.get("id"): doc
            for doc in dense_docs
            if doc.metadata.get("id")
            and self._matches_metadata_filter(doc, plan.metadata_filter)
        }
        sparse_ids = self._sparse_ids(
            plan.semantic_query,
            candidate_k,
            plan.metadata_filter,
        )
        fused = rrf_fuse([list(dense_by_id), sparse_ids])
        ranked: list[HybridResult] = []
        for item_id, score in fused:
            document = dense_by_id.get(item_id) or self._documents.get(item_id)
            if document is None:
                continue
            metadata_text = " ".join(
                str(document.metadata.get(field, ""))
                for field in ("ten_van_ban", "chuong", "dieu", "tieu_de_dieu", "khoan")
            )
            adjusted = score + facet_score(
                query,
                f"{metadata_text} {document.page_content}",
                self.domain,
            )
            ranked.append(HybridResult(document, adjusted))
        ranked.sort(
            key=lambda result: (
                -result.fused_score,
                str(result.document.metadata.get("id", "")),
            )
        )
        decision = assess_query_complexity(query, self.domain, ranked[:k])
        use_reranker = bool(getattr(self.settings, "reranker_enabled", False)) and decision.should_rerank
        if getattr(self.settings, "reranker_enabled", False):
            logger.info(
                "Reranker decision: domain=%s score=%s enabled=%s reasons=%s",
                self.domain,
                decision.score,
                use_reranker,
                ",".join(decision.reasons) or "none",
            )
        reranked = rerank(retrieval_query, ranked, self.settings, enabled=use_reranker)[:k]
        return self._expand_parent_context(reranked, query)

_RETRIEVERS: dict[tuple[str, str, str, str], HybridRetriever] = {}


def invalidate_hybrid_retriever(settings: Settings, domain: str) -> None:
    """Drop the cached BM25 index for a domain after ingest/update."""
    config = settings.domain_config(domain)
    prefix = (str(settings.chroma_path), config.collection_name, settings.embedding_model, config.name)
    _RETRIEVERS.pop(prefix, None)


def get_hybrid_retriever(settings: Settings, domain: str = "labor") -> HybridRetriever:
    config = settings.domain_config(domain)
    key = (str(settings.chroma_path), config.collection_name, settings.embedding_model, config.name)
    if key not in _RETRIEVERS:
        _RETRIEVERS[key] = HybridRetriever(settings, domain=config.name)
    return _RETRIEVERS[key]
