"""Deterministic clarification gates for underspecified legal questions."""

from __future__ import annotations

from .query_normalization import normalize_for_routing


def clarification_for_query(query: str, domain: str) -> str | None:
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
        tax_question = any(term in routing for term in (
            "phai nop thue", "cac loai thue", "nhung loai thue", "nghia vu thue", "khai thue",
        ))
        if tax_question and not tax_subject:
            return "Bạn muốn hỏi nghĩa vụ thuế của hộ kinh doanh, cá nhân kinh doanh hay doanh nghiệp?"

    return None
