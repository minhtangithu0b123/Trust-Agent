"""Deterministic query facets used to improve legal evidence ranking.

This is deliberately rule-based and small.  It extracts stable constraints
from the query; it does not generate legal facts or metadata filters.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from .query_normalization import normalize_for_routing


@dataclass(frozen=True)
class QueryFacets:
    required_phrases: tuple[str, ...] = ()
    excluded_phrases: tuple[str, ...] = ()
    topic_phrases: tuple[str, ...] = ()


_VEHICLES = {
    "specialized_vehicle": ("xe may chuyen dung", "may keo"),
    "car": ("o to", "oto", "xe hoi", "xe con"),
    "motorbike": ("xe may", "xe moto", "moto", "xe gan may", "tay ga"),
    "pedestrian": ("nguoi di bo", "di bo"),
    "bicycle": ("xe dap", "xe dap may", "xe tho so"),
}

_DOMAIN_TOPICS = {
    "traffic": (
        ("nong do con", ("nong do con", "ruou bia")),
        ("mu bao hiem", ("mu bao hiem", "cai quai")),
        ("vuot den do", ("den tin hieu", "den do", "tin hieu giao thong")),
        ("toc do", ("toc do", "gioi han toc do")),
        ("tai nan", ("tai nan giao thong", "tai nan")),
        ("giay phep lai xe", ("giay phep lai xe", "bang lai")),
    ),
    "labor": (
        ("hop dong lao dong", ("hop dong lao dong", "giao ket hop dong")),
        ("thu viec", ("thu viec", "hop dong thu viec", "thoi gian thu viec")),
        ("nghi phep", ("nghi hang nam", "nghi phep", "ngay nghi")),
        ("tien luong", ("tien luong", "luong")),
        ("ky luat", ("ky luat lao dong", "xu ly ky luat")),
        ("bao hiem xa hoi", ("bao hiem xa hoi", "bao hiem")),
        ("tai nan lao dong", ("tai nan lao dong", "benh nghe nghiep")),
    ),
    "accounting": (
        ("ca nhan kinh doanh", ("ca nhan kinh doanh", "ho kinh doanh")),
        ("loai thue", ("loai thue", "nghia vu thue", "thue phai nop")),
        ("hoa don dien tu", ("hoa don dien tu", "hoa don")),
        ("thue gia tri gia tang", ("thue gia tri gia tang", "gtgt", "vat")),
        ("nguyen tac ke toan", ("nguyen tac ke toan", "ke toan")),
        ("quyet toan thue", ("quyet toan thue", "quyet toan")),
        ("bao cao tai chinh", ("bao cao tai chinh", "bao cao")),
    ),
}


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def extract_query_facets(query: str, domain: str) -> QueryFacets:
    """Extract only recognized, safe constraints from a user query."""
    routing = normalize_for_routing(query)
    required: list[str] = []
    excluded: list[str] = []
    topics: list[str] = []

    if domain == "traffic":
        # "mô tô" normalizes to "mo to" and must be treated as a motorbike.
        if _contains(routing, "mo to"):
            required.append("motorbike")
            for other_group, other_phrases in _VEHICLES.items():
                if other_group != "motorbike":
                    excluded.extend(other_phrases)
        for group, phrases in _VEHICLES.items():
            if required:
                break
            if any(_contains(routing, phrase) for phrase in phrases):
                required.append(group)
                for other_group, other_phrases in _VEHICLES.items():
                    if other_group != group:
                        excluded.extend(other_phrases)
                break

    for canonical, signals in _DOMAIN_TOPICS.get(domain, ()):
        if any(signal in routing for signal in signals):
            topics.append(canonical)

    return QueryFacets(tuple(required), tuple(excluded), tuple(topics))


def facet_score(query: str, text: str, domain: str) -> float:
    """Return a deterministic ranking adjustment for recognized constraints."""
    facets = extract_query_facets(query, domain)
    if not facets.required_phrases and not facets.topic_phrases:
        return 0.0
    document = normalize_for_routing(text)
    score = 0.0
    if facets.required_phrases:
        group = facets.required_phrases[0]
        vehicle_terms = _VEHICLES[group]
        if any(_contains(document, normalize_for_routing(term)) for term in vehicle_terms):
            score += 0.08
        elif any(_contains(document, normalize_for_routing(term)) for term in facets.excluded_phrases):
            score -= 0.10
    if facets.topic_phrases:
        matched = sum(
            1 for topic in facets.topic_phrases
            if any(_contains(document, normalize_for_routing(signal)) for signal in dict(_DOMAIN_TOPICS.get(domain, ())).get(topic, ()))
        )
        score += 0.04 * (matched / len(facets.topic_phrases))

    # Questions asking for the maximum trial duration target Điều 25. The
    # adjacent trial articles cover contract conditions and notification, but
    # should not outrank the duration rule when the reranker is disabled.
    routing = normalize_for_routing(query)
    if (
        domain == "labor"
        and "thu viec" in routing
        and any(term in routing for term in ("toi da", "bao nhieu ngay", "bao lau"))
        and _contains(document, "dieu 25")
    ):
        score += 0.14

    if (
        domain == "labor"
        and any(phrase in routing for phrase in ("nghi phep", "nghi hang nam"))
        and any(term in routing for term in ("bao nhieu ngay", "so ngay", "duoc nghi"))
        and _contains(document, "dieu 113")
    ):
        score += 0.14
    return score
