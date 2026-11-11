"""Labor domain adapter for the shared ReAct agent foundation."""

from __future__ import annotations

from typing import Any

from ..config import get_settings
from ..query_normalization import clean_query, expand_query_for_retrieval, normalize_for_routing
from ..retrieval import get_hybrid_retriever
from .base import (
    AgentFinalOutput as LaborFinalOutput,
    AgentProviderError,
    DomainAgentSpec,
    DomainAgentState as LaborAgentState,
    INSUFFICIENT_EVIDENCE,
    MAX_STEPS,
    ToolDecision,
    build_domain_agent_graph,
    build_openai_model,
    get_domain_document,
    run_domain_agent,
    search_domain_law,
)

LABOR_DOMAIN = "labor"
AGENT_POLICY = """Bạn là ReAct Labor Agent chuyên tra cứu pháp luật lao động Việt Nam.
Luôn gọi evidence trước khi trả lời và chỉ sử dụng công cụ labor được cung cấp.
Tập trung vào hợp đồng lao động, tiền lương, nghỉ phép, kỷ luật, quyền người lao động và nghĩa vụ người sử dụng lao động.
Không dùng kiến thức bên ngoài evidence; không bịa số hiệu, Điều, Khoản, mức tiền, ngày hiệu lực hoặc citation.
Có thể search nhiều lần hoặc lấy một document cụ thể nếu evidence chưa đủ.
Nếu không đủ căn cứ, phải trả đúng: "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận."
Nếu metadata hiệu lực là unknown hoặc trống, không khẳng định văn bản vẫn đang có hiệu lực; nói rõ trạng thái hiệu lực chưa được xác minh khi câu hỏi cần thông tin hiện hành.
Phân biệt "Quy định pháp luật" và "Suy luận theo tình huống" nếu có suy luận.
Chỉ dùng cited_document_ids xuất hiện trong evidence của lượt chạy này.
"""
SPEC = DomainAgentSpec(LABOR_DOMAIN, "Labor Agent", AGENT_POLICY)


def search_labor_law(query: str, k: int = 5) -> list[dict[str, Any]]:
    settings = get_settings()
    original = clean_query(query)
    expanded = expand_query_for_retrieval(original, normalize_for_routing(original), LABOR_DOMAIN)
    return search_domain_law(settings, LABOR_DOMAIN, get_hybrid_retriever, expanded, k)


def get_labor_document(document_id: str) -> dict[str, Any] | None:
    return get_domain_document(get_settings(), LABOR_DOMAIN, document_id)


def _build_model(settings):
    return build_openai_model(settings)


def build_labor_agent_graph(model: Any):
    return build_domain_agent_graph(SPEC, model, search_labor_law, get_labor_document)


def run_labor_agent(query: str, k: int = 5, model: Any | None = None, max_steps: int = MAX_STEPS, sub_queries: list[str] | None = None) -> dict[str, Any]:
    settings = get_settings()
    cleaned_query = clean_query(query)
    return run_domain_agent(
        cleaned_query, k, settings, SPEC, search_labor_law, get_labor_document, model=model, max_steps=max_steps, sub_queries=sub_queries
    )
