"""Deterministic clarification gates for underspecified legal questions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import re

from .query_normalization import normalize_for_routing


@dataclass(frozen=True)
class QuerySlots:
    """Small, auditable slot state used before legal retrieval."""

    domain: str
    vehicle: str | None = None
    party: str | None = None
    taxpayer_type: str | None = None
    topic: str | None = None


@dataclass(frozen=True)
class ClarificationDecision:
    action: Literal["clarify", "proceed"]
    slots: QuerySlots
    missing_slots: tuple[str, ...] = ()
    question: str | None = None
    source: str = "rules"


def _has_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def fill_query_slots(query: str, domain: str) -> QuerySlots:
    """Extract only explicit slots; never infer a legal fact from retrieval."""
    routing = normalize_for_routing(query)
    vehicle = None
    if any(_has_phrase(routing, term) for term in ("xe may", "xe mo to", "xe gan may", "xe may chuyen dung")):
        vehicle = "motorbike"
    elif any(_has_phrase(routing, term) for term in ("o to", "oto", "xe hoi", "xe con")):
        vehicle = "car"
    elif any(_has_phrase(routing, term) for term in ("xe dap", "xe dap dien")):
        vehicle = "bicycle"

    party = None
    if _has_phrase(routing, "nguoi lao dong"):
        party = "employee"
    elif _has_phrase(routing, "nguoi su dung lao dong"):
        party = "employer"

    taxpayer_type = None
    for term, value in ((
        ("ho kinh doanh", "household_business"),
        ("ca nhan kinh doanh", "individual_business"),
        ("doanh nghiep", "enterprise"),
        ("cong ty", "company"),
    )):
        if _has_phrase(routing, term):
            taxpayer_type = value
            break

    topic = None
    for term, value in ((
        ("toc do", "speed"), ("mu bao hiem", "helmet"),
        ("day an toan", "seatbelt"), ("nong do con", "alcohol"),
        ("cham dut hop dong", "termination"), ("thue", "tax"),
    )):
        if _has_phrase(routing, term):
            topic = value
            break
    return QuerySlots(domain, vehicle, party, taxpayer_type, topic)


def build_clarification_decision(query: str, domain: str) -> ClarificationDecision:
    """Combine slot filling with the existing deterministic clarification gates."""
    slots = fill_query_slots(query, domain)
    question = _rule_question_for_query(query, domain)
    if question is None:
        return ClarificationDecision("proceed", slots, source="rules")
    missing = ("vehicle",) if domain == "traffic" else ("party",) if domain == "labor" else ("taxpayer_type",)
    return ClarificationDecision("clarify", slots, missing, question, source="rules")


def _rule_question_for_query(query: str, domain: str) -> str | None:
    """Return one focused follow-up question when a required facet is missing.

    This runs before retrieval so an agent cannot answer with evidence for the
    wrong vehicle, role, or taxpayer type.  It intentionally stays rule-based;
    the LLM is not allowed to invent the missing fact.
    """
    routing = normalize_for_routing(query)

    if domain == "traffic":
        vehicle = any(term in routing for term in (
            "xe may", "xe mo to", "xe gan may", "xe may chuyen dung",
            "o to", "oto", "xe hoi", "xe dap", "xe dap dien",
        ))
        if any(term in routing for term in ("mu bao hiem", "doi mu", "doi non")) and not vehicle:
            return "Bạn muốn tra cứu loại phương tiện nào: xe máy, ô tô hay xe đạp điện?"
        if any(term in routing for term in ("toc do", "vuot qua toc do", "chay qua toc do")) and not vehicle:
            return "Bạn muốn hỏi về ô tô, xe máy hay loại phương tiện khác?"
        if any(term in routing for term in ("day an toan", "day dai an toan", "that day")) and not vehicle:
            return "Bạn muốn hỏi người lái hay người được chở trên ô tô?"
        if any(term in routing for term in ("cho qua so nguoi", "qua so nguoi", "cho qua nguoi")) and not vehicle:
            return "Bạn muốn hỏi xe máy hay ô tô chở quá số người quy định?"
        if any(term in routing for term in ("khong mang bang lai", "khong co bang lai", "khong co giay phep lai xe", "khong mang giay phep lai xe")) and not vehicle:
            return "Bạn muốn tra cứu trường hợp này đối với ô tô hay xe máy?"
        if (
            any(term in routing for term in ("sang hom sau", "uong bia", "ruou tu toi", "con nong do con"))
            and any(term in routing for term in ("nong do con", "ruou bia"))
            and not vehicle
        ):
            return "Bạn muốn hỏi mức phạt đối với ô tô, xe máy hay loại phương tiện nào?"

    if domain == "labor":
        termination = any(term in routing for term in (
            "don phuong cham dut hop dong", "bao truoc khi cham dut hop dong",
        ))
        has_party = any(term in routing for term in (
            "nguoi lao dong", "nguoi su dung lao dong", "nguoi lao dong va nguoi su dung lao dong",
        ))
        if termination and not has_party:
            return "Bạn muốn hỏi thời hạn báo trước của người lao động hay người sử dụng lao động?"

    if domain == "accounting":
        tax_subject = any(term in routing for term in (
            "ho kinh doanh", "ca nhan kinh doanh", "doanh nghiep", "cong ty", "to chuc",
        ))
        personal_transfer = any(term in routing for term in (
            "cha me", "bo me", "con", "vo chong", "anh chi em",
            "tang cho", "qua tang", "thua ke", "chuyen nhuong",
            "ban nha", "bat dong san", "ban xe", "ban o to",
        ))
        tax_question = any(term in routing for term in (
            "phai nop thue", "cac loai thue", "nhung loai thue", "nghia vu thue", "khai thue",
        ))
        if tax_question and not tax_subject and not personal_transfer:
            return "Bạn muốn hỏi nghĩa vụ thuế của hộ kinh doanh, cá nhân kinh doanh hay doanh nghiệp?"

    return None


def clarification_for_query(query: str, domain: str) -> str | None:
    """Backward-compatible facade returning only the follow-up text."""
    decision = build_clarification_decision(query, domain)
    return decision.question if decision.action == "clarify" else None
