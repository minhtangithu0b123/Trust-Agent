"""Deterministic planning helpers for controlled multi-hop retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from .query_normalization import clean_query, normalize_for_routing


@dataclass(frozen=True)
class HopPlan:
    hop: int
    missing_facets: tuple[str, ...]
    queries: tuple[str, ...]


_DOMAIN_FACETS = {
    "traffic": {
        "penalty": ("phat", "muc phat", "xu phat"),
        "points": ("tru diem", "diem bang lai", "giay phep lai xe"),
        "supplemental": ("xu phat bo sung", "tuoc", "tam giu"),
        "exception": ("ngoai le", "truong hop", "dieu kien"),
    },
    "labor": {
        "condition": ("dieu kien", "doi tuong", "ap dung"),
        "exception": ("ngoai le", "truong hop", "khong ap dung"),
        "limit": ("toi da", "so ngay", "muc", "thoi han"),
    },
    "accounting": {
        "obligation": ("phai", "bat buoc", "trach nhiem"),
        "exception": ("ngoai le", "khong bat buoc", "truong hop"),
        "effective_date": ("hieu luc", "tu ngay", "ngay co hieu luc"),
        "transition": ("chuyen tiep", "truoc", "sau", "thay the"),
    },
}


_HOP_TEMPLATES = {
    "traffic": {
        "penalty": "{q} mức phạt tiền điều khoản áp dụng",
        "points": "{q} bị trừ bao nhiêu điểm giấy phép lái xe",
        "supplemental": "{q} hình thức xử phạt bổ sung tước giấy phép lái xe",
        "exception": "{q} điều kiện ngoại lệ đối tượng áp dụng",
    },
    "labor": {
        "condition": "{q} điều kiện và đối tượng áp dụng",
        "exception": "{q} trường hợp ngoại lệ không áp dụng",
        "limit": "{q} thời hạn mức tối đa căn cứ điều khoản",
    },
    "accounting": {
        "obligation": "{q} nghĩa vụ và đối tượng phải thực hiện",
        "exception": "{q} trường hợp ngoại lệ không bắt buộc",
        "effective_date": "{q} ngày có hiệu lực",
        "transition": "{q} quy định chuyển tiếp trước và sau thời điểm hiệu lực",
    },
}


def _has_facet(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def plan_next_hop(
    query: str,
    domain: str,
    evidence: list[dict[str, object]],
    hop: int = 2,
    max_hops: int = 2,
) -> HopPlan:
    """Return bounded follow-up queries only for facets absent from evidence."""
    if hop > max_hops:
        return HopPlan(hop, (), ())
    routing_query = normalize_for_routing(query)
    if not routing_query or domain not in _DOMAIN_FACETS:
        return HopPlan(hop, (), ())

    # Only activate multi-hop for questions that ask for conditions,
    # exceptions, dates, consequences, or multiple parts.
    trigger_terms = (
        "ngoai le", "truong hop", "dieu kien", "hieu luc", "chuyen tiep",
        "phai", "bat buoc", "bao nhieu", "tru diem", "xu phat bo sung",
    )
    if not any(term in routing_query for term in trigger_terms):
        return HopPlan(hop, (), ())

    evidence_text = " ".join(
        normalize_for_routing(
            " ".join([
                str(item.get("text", "")),
                str(item.get("metadata", {}).get("dieu", "")) if isinstance(item.get("metadata"), dict) else "",
                str(item.get("metadata", {}).get("khoan", "")) if isinstance(item.get("metadata"), dict) else "",
            ])
        )
        for item in evidence
    )
    required: list[str] = []
    facets = _DOMAIN_FACETS[domain]
    for facet, terms in facets.items():
        if facet == "points":
            requested = "diem" in routing_query and ("tru" in routing_query or "bang lai" in routing_query)
            present = "tru diem" in evidence_text
        else:
            requested = any(term in routing_query for term in terms)
            present = _has_facet(evidence_text, terms)
        if requested and not present:
            required.append(facet)
    templates = _HOP_TEMPLATES[domain]
    queries = tuple(
        clean_query(templates[facet].format(q=clean_query(query)))
        for facet in required
        if facet in templates
    )
    return HopPlan(hop, tuple(required), queries)
