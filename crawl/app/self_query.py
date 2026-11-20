"""Rule-based self-query planning for legal retrieval.

The parser extracts safe metadata constraints from a user's query while
preserving the original semantic query. It intentionally does not call an
LLM, so a model cannot invent arbitrary metadata filters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .query_normalization import clean_query, normalize_for_routing


CANONICAL_DOMAINS = {"traffic", "labor", "accounting"}

_TRAFFIC_VEHICLE_ARTICLES = {
    "specialized_vehicle": "Điều 8",
    "car": "Điều 6",
    "motorbike": "Điều 7",
    "pedestrian": "Điều 9",
    "bicycle": "Điều 9",
}

_SO_HIEU_RE = re.compile(
    r"\b\d+\/\d{4}\/[A-ZĐ][A-ZĐ0-9-]*\b", re.IGNORECASE
)
_DIEU_RE = re.compile(r"\b(?:điều|dieu)\s+(\d+[A-Za-z]?)\b", re.IGNORECASE)
_KHOAN_RE = re.compile(r"\b(?:khoản|khoan)\s+(\d+[A-Za-z]?)\b", re.IGNORECASE)


@dataclass(frozen=True)
class QueryPlan:
    semantic_query: str
    metadata_filter: dict[str, Any]


def _contains_phrase(value: str, phrase: str) -> bool:
    """Match a normalized phrase without substring collisions (e.g. 'o to' in 'cao toc')."""
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", value) is not None


def _vehicle_group(routing_query: str) -> str | None:
    if _contains_phrase(routing_query, "xe may chuyen dung") or _contains_phrase(routing_query, "may keo"):
        return "specialized_vehicle"
    if any(_contains_phrase(routing_query, term) for term in ("o to", "oto", "xe hoi", "xe con")):
        return "car"
    if any(_contains_phrase(routing_query, term) for term in ("xe may", "mo to", "xe gan may", "tay ga")):
        return "motorbike"
    if any(_contains_phrase(routing_query, term) for term in ("nguoi di bo", "di bo")):
        return "pedestrian"
    if any(_contains_phrase(routing_query, term) for term in ("xe dap", "xe dap may", "xe tho so")):
        return "bicycle"
    return None


def _vehicle_groups(routing_query: str) -> set[str]:
    # Check the most specific expression first. Otherwise "xe may chuyen
    # dung" also matches the generic "xe may" branch and disables filtering.
    groups: set[str] = set()
    specialized = _contains_phrase(routing_query, "xe may chuyen dung") or _contains_phrase(routing_query, "may keo")
    if specialized:
        groups.add("specialized_vehicle")
    if not specialized and any(_contains_phrase(routing_query, term) for term in ("o to", "oto", "xe hoi", "xe con")):
        groups.add("car")
    if not specialized and any(_contains_phrase(routing_query, term) for term in ("xe may", "mo to", "xe gan may", "tay ga")):
        groups.add("motorbike")
    if any(_contains_phrase(routing_query, term) for term in ("nguoi di bo", "di bo")):
        groups.add("pedestrian")
    if any(_contains_phrase(routing_query, term) for term in ("xe dap", "xe dap may", "xe tho so")):
        groups.add("bicycle")
    return groups


def _traffic_topics(routing_query: str) -> list[str]:
    """Map all common traffic wording to normalized clause topics."""
    checks = (
        ("helmet", ("mu bao hiem", "doi mu")),
        ("phone_use", ("dien thoai", "thiet bi dien tu")),
        ("passenger_overload", ("cho 2 nguoi", "cho theo 2 nguoi", "cho qua so nguoi")),
        ("red_light", ("vuot den do", "den tin hieu")),
        ("seatbelt", ("day an toan", "day bao hiem")),
        ("alcohol", ("nong do con", "ruou bia")),
        ("speed", ("toc do", "qua toc")),
    )
    return [topic for topic, signals in checks if any(signal in routing_query for signal in signals)]


def build_query_plan(query: str, domain: str) -> QueryPlan:
    """Build a safe semantic query plus validated metadata constraints."""
    if domain not in CANONICAL_DOMAINS:
        raise ValueError(f"Unsupported domain: {domain}")

    semantic_query = clean_query(query)
    routing_query = normalize_for_routing(semantic_query)
    metadata_filter: dict[str, Any] = {"domain": domain}

    so_hieu = _SO_HIEU_RE.search(semantic_query)
    dieu = _DIEU_RE.search(semantic_query)
    khoan = _KHOAN_RE.search(semantic_query)

    if so_hieu:
        metadata_filter["so_hieu"] = so_hieu.group(0)
    if dieu:
        metadata_filter["dieu"] = f"Điều {dieu.group(1)}"
    if khoan:
        metadata_filter["khoan"] = f"Khoản {khoan.group(1)}"

    # Traffic penalties are organized by vehicle class. Constrain a query
    # naming exactly one class to the corresponding article, so evidence for
    # motorcycles cannot be presented as an answer for cars (or vice versa).
    if domain == "traffic" and not dieu:
        groups = _vehicle_groups(routing_query)
        if len(groups) == 1:
            group = next(iter(groups))
            metadata_filter["dieu"] = _TRAFFIC_VEHICLE_ARTICLES[group]
            metadata_filter["dieu"] = {
                "specialized_vehicle": "Điều 8",
                "car": "Điều 6",
                "motorbike": "Điều 7",
                "pedestrian": "Điều 9",
                "bicycle": "Điều 9",
            }[group]
            # The same offence is placed in different clauses by vehicle
            # class in Decree 168. Prevent a generic article clause from
            # outranking the actual red-light provision.
            if "vuot den do" in routing_query or "den tin hieu" in routing_query:
                metadata_filter["khoan"] = "Khoản 9" if group == "car" else "Khoản 7"
            elif "cao toc" in routing_query and group == "motorbike":
                metadata_filter["khoan"] = "Khoản 7"
            elif "speed" in _traffic_topics(routing_query):
                metadata_filter["khoan"] = "Khoản 5" if group == "car" else "Khoản 4"
            elif "mu bao hiem" in routing_query and group == "motorbike":
                metadata_filter["khoan"] = "Khoản 2"
            topics = _traffic_topics(routing_query)
            if topics:
                metadata_filter["traffic_topics"] = topics[0] if len(topics) == 1 else topics

    # These articles are the legal cluster for trial-period questions. Keep
    # all three because the answer may require the maximum duration, contract
    # conditions, and the employer's notification duty together.
    if domain == "labor" and not dieu and "thu viec" in routing_query:
        metadata_filter["dieu"] = ["Điều 24", "Điều 25", "Điều 26", "Điều 27"]

    if domain == "accounting" and not dieu and any(
        phrase in routing_query for phrase in (
            "cha me tang nha cho con",
            "bo me tang nha cho con",
            "tang nha cho con",
            "tang bat dong san cho con",
        )
    ):
        metadata_filter["dieu"] = "Điều 4"
        metadata_filter["khoan"] = "Khoản 1"

    if domain == "labor" and not dieu and any(
        phrase in routing_query for phrase in ("nghi phep", "nghi hang nam", "ngay phep")
    ):
        if "chua du 12" in routing_query or "chua du 12 thang" in routing_query:
            metadata_filter["dieu"] = ["Điều 113", "Điều 66"]
        elif "du 5 nam" in routing_query:
            metadata_filter["dieu"] = ["Điều 113", "Điều 114"]
        else:
            metadata_filter["dieu"] = "Điều 113"
        if any(term in routing_query for term in ("bao nhieu ngay", "so ngay", "duoc nghi")):
            metadata_filter["khoan"] = ["Khoản 1", "Khoản 2"]

    # Resignation questions are commonly phrased as simply "nghỉ việc".
    # Keep the three termination articles together because the answer may
    # need to distinguish employee notice, mutual termination, and employer
    # termination instead of silently selecting an unrelated labor clause.
    if (
        domain == "labor"
        and not dieu
        and any(
            phrase in routing_query
            for phrase in ("nghi viec", "bao truoc", "don phuong cham dut", "cham dut hop dong")
        )
        and not any(phrase in routing_query for phrase in ("nghi phep", "nghi hang nam", "ngay phep"))
    ):
        metadata_filter["dieu"] = ["Điều 35", "Điều 36", "Điều 37"]

    if domain == "labor" and not dieu and any(
        phrase in routing_query for phrase in ("chua ky hop dong", "chua co hop dong", "khong ky hop dong")
    ):
        metadata_filter["dieu"] = ["Điều 13", "Điều 14", "Điều 34", "Điều 36", "Điều 37", "Điều 41", "Điều 46"]

    if domain == "labor" and not dieu and any(
        phrase in routing_query for phrase in ("lam them", "ngoai gio", "them gio")
    ):
        metadata_filter["dieu"] = ["Điều 98", "Điều 106", "Điều 107"]

    # Multiple-employer questions need the provisions on the first contract,
    # health insurance, and occupational accident insurance together.
    if domain == "labor" and not dieu and any(
        phrase in routing_query for phrase in ("nhieu hop dong", "hai cong ty", "2 cong ty", "hai hop dong")
    ):
        metadata_filter["dieu"] = ["Điều 21", "Điều 43", "Điều 168"]

    return QueryPlan(
        semantic_query=semantic_query,
        metadata_filter=metadata_filter,
    )
