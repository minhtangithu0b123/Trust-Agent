"""Domain overview responses for broad legal questions."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import Settings
from .domains import DomainConfig
from .query_normalization import normalize_for_routing
from .vectorstore import get_vectorstore

_OVERVIEW_MARKERS = (
    "co gi",
    "co nhung gi",
    "gom nhung gi",
    "gom gi",
    "co nhung noi dung nao",
    "noi dung gi",
    "tong quan",
    "pham vi",
    "quy dinh nhung gi",
)

_DOMAIN_MARKERS = {
    "labor": ("luat lao dong", "bo luat lao dong", "lao dong"),
    "traffic": ("luat giao thong", "giao thong", "duong bo"),
    "accounting": ("luat ke toan", "ke toan", "thue", "hoa don"),
}

# A specific legal subject must go through retrieval even when the user uses
# wording such as "có những nội dung gì". Otherwise a question like
# "Hợp đồng lao động cần có những nội dung gì?" is incorrectly treated as a
# domain overview request.
_SPECIFIC_SUBJECT_MARKERS = (
    "hop dong lao dong", "nghi phep", "nghi hang nam", "tien luong",
    "quyen loi nguoi lao dong", "ky luat lao dong", "thai san",
    "nong do con", "vuot den do", "mu bao hiem", "tai nan giao thong",
    "hoa don dien tu", "thue gia tri gia tang", "thue thu nhap",
    "quyet toan thue", "nguyen tac ke toan",
)


def detect_overview_domain(query: str) -> str | None:
    """Return a canonical domain only for clearly broad overview queries."""
    normalized = normalize_for_routing(query)
    if any(marker in normalized for marker in _SPECIFIC_SUBJECT_MARKERS):
        return None
    if not any(marker in normalized for marker in _OVERVIEW_MARKERS):
        return None
    for domain, markers in _DOMAIN_MARKERS.items():
        if any(marker in normalized for marker in markers):
            return domain
    return None


def _clean(value: Any) -> str:
    return str(value or "").strip()


def build_domain_overview(settings: Settings, config: DomainConfig) -> dict[str, Any]:
    """Build a compact metadata-driven map of a legal domain."""
    store = get_vectorstore(settings, config.name)
    payload = store.get(include=["metadatas"])
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    chapter_articles: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    matched_count = 0

    for metadata in payload.get("metadatas", []):
        metadata = metadata or {}
        if metadata.get("domain") != config.name:
            continue
        matched_count += 1
        key = (
            _clean(metadata.get("so_hieu")),
            _clean(metadata.get("ten_van_ban")),
            _clean(metadata.get("source")),
        )
        grouped.setdefault(
            key,
            {"so_hieu": key[0], "ten_van_ban": key[1], "source": key[2], "chapters": {}},
        )
        chapter = _clean(metadata.get("chuong")) or "Chưa xác định"
        article = _clean(metadata.get("dieu"))
        chapter_articles[(key[0], key[1], key[2], chapter)].add(article)

    for (so_hieu, ten_van_ban, source, chapter), articles in chapter_articles.items():
        document = grouped[(so_hieu, ten_van_ban, source)]
        document["chapters"][chapter] = {
            "chuong": chapter,
            "article_count": len({item for item in articles if item}),
            "articles": sorted(item for item in articles if item),
        }

    documents = []
    for document in grouped.values():
        chapters = sorted(document["chapters"].values(), key=lambda item: item["chuong"])
        documents.append({**document, "chapters": chapters})
    documents.sort(key=lambda item: (item["ten_van_ban"], item["so_hieu"]))

    has_corpus = bool(documents)
    overview = {
        "domain": config.name,
        "collection": config.collection_name,
        "document_count": matched_count,
        "documents": documents,
        "status": "overview" if has_corpus else "no_corpus",
        "next_step": "Bạn muốn tìm hiểu cụ thể phần nào? Hãy nêu chủ đề, hành vi hoặc Điều/Khoản cần tra cứu.",
    }
    overview["answer"] = (
        format_overview_answer(overview)
        if has_corpus
        else "Chưa có dữ liệu pháp luật cho lĩnh vực này. Hãy ingest corpus trước khi tra cứu."
    )
    return overview


def format_overview_answer(overview: dict[str, Any]) -> str:
    """Create a short UI-friendly answer from the metadata map."""
    lines = ["Dữ liệu pháp luật hiện có gồm các nhóm/chương chính:"]
    for document in overview.get("documents", []):
        chapters = [chapter["chuong"] for chapter in document.get("chapters", []) if chapter.get("chuong")]
        if chapters:
            lines.append(f"- {document.get('ten_van_ban') or 'Văn bản'}: {', '.join(chapters[:12])}")
    lines.append(overview["next_step"])
    return "\n".join(lines)
