"""Accounting and tax domain adapter for the shared ReAct agent foundation."""

from __future__ import annotations

from typing import Any

from ..config import get_settings
from ..clarification import build_clarification_decision
from ..query_normalization import clean_query, expand_query_for_retrieval, normalize_for_routing
from ..retrieval import get_hybrid_retriever
from .base import (
    AgentFinalOutput as AccountingFinalOutput,
    AgentProviderError,
    DomainAgentSpec,
    DomainAgentState as AccountingAgentState,
    INSUFFICIENT_EVIDENCE,
    MAX_STEPS,
    ToolDecision,
    build_domain_agent_graph,
    build_openai_model,
    get_domain_document,
    run_domain_agent,
    search_domain_law,
)

ACCOUNTING_DOMAIN = "accounting"
AGENT_POLICY = """Bạn là ReAct Accounting Agent chuyên tra cứu tài liệu kế toán và thuế Việt Nam.
Luôn gọi evidence trước khi trả lời và chỉ sử dụng công cụ accounting được cung cấp.
Không khẳng định toàn bộ pháp luật kế toán hoặc thuế đã được bao phủ; chỉ trả lời trong phạm vi evidence đã truy xuất.
Không dùng kiến thức bên ngoài evidence; không bịa số hiệu, Điều, Khoản, mức tiền, ngày hiệu lực hoặc citation.
Có thể search nhiều lần hoặc lấy một document cụ thể nếu evidence chưa đủ.
Nếu không đủ căn cứ, phải trả đúng: "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận."
Phân biệt "Quy định pháp luật" và "Suy luận theo tình huống" nếu có suy luận.
Chỉ dùng cited_document_ids xuất hiện trong evidence của lượt chạy này.
Khi trả lời về hóa đơn điện tử của hộ/cá nhân kinh doanh, phải nêu rõ điều kiện và ngoại lệ đúng theo evidence; không suy rộng thành "mọi hộ kinh doanh luôn phải dùng cùng một loại hóa đơn".
Nếu đề cập căn cứ, phải dùng đúng tên văn bản và số hiệu trong CITATION, không thay bằng các tên chung như "Luật thuế".
Chỉ trả lời đúng nội dung câu hỏi hiện tại; không lặp lại câu trả lời của lượt trước và không thêm Điều/Khoản liên quan nếu evidence không trực tiếp hỗ trợ.
Với quà tặng bất động sản giữa cha mẹ và con, phải ưu tiên kiểm tra trường hợp miễn thuế tại Điều 4(1). Không áp dụng ngưỡng 20 triệu hoặc thuế suất quà tặng chung nếu evidence xác định quan hệ cha mẹ-con thuộc diện miễn.
Với cá nhân bán hàng online, phải tách riêng ngưỡng/thuế VAT, ngưỡng/thuế PIT và trách nhiệm khấu trừ-khai-nộp của nền tảng. Không trình bày một ngưỡng là áp dụng đồng thời cho cả VAT và PIT.
"""
SPEC = DomainAgentSpec(ACCOUNTING_DOMAIN, "Tax Agent", AGENT_POLICY)


def search_accounting_law(query: str, k: int = 5) -> list[dict[str, Any]]:
    settings = get_settings()
    original = clean_query(query)
    expanded = expand_query_for_retrieval(original, normalize_for_routing(original), ACCOUNTING_DOMAIN)
    return search_domain_law(settings, ACCOUNTING_DOMAIN, get_hybrid_retriever, expanded, k)


def get_accounting_document(document_id: str) -> dict[str, Any] | None:
    return get_domain_document(get_settings(), ACCOUNTING_DOMAIN, document_id)


def _build_model(settings):
    return build_openai_model(settings)


def build_accounting_agent_graph(model: Any):
    return build_domain_agent_graph(SPEC, model, search_accounting_law, get_accounting_document)


def run_accounting_agent(query: str, k: int = 5, model: Any | None = None, max_steps: int = MAX_STEPS, sub_queries: list[str] | None = None) -> dict[str, Any]:
    settings = get_settings()
    cleaned_query = clean_query(query)
    clarification = build_clarification_decision(cleaned_query, ACCOUNTING_DOMAIN)
    if clarification.action == "clarify":
        return {"query": cleaned_query, "answer": clarification.question, "status": "needs_clarification", "citations": [], "clarification_slots": clarification.missing_slots}
    return run_domain_agent(
        cleaned_query, k, settings, SPEC, search_accounting_law, get_accounting_document, model=model, max_steps=max_steps, sub_queries=sub_queries
    )
