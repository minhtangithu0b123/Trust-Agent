"""Labor domain adapter for the shared ReAct agent foundation."""

from __future__ import annotations

import logging
from typing import Any

from ..config import get_settings
from ..clarification import clarification_for_query
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
logger = logging.getLogger(__name__)
AGENT_POLICY = """Bạn là ReAct Labor Agent chuyên tra cứu pháp luật lao động Việt Nam.
Luôn gọi evidence trước khi trả lời và chỉ sử dụng công cụ labor được cung cấp.
Tập trung vào hợp đồng lao động, tiền lương, nghỉ phép, kỷ luật, quyền người lao động và nghĩa vụ người sử dụng lao động.
Không dùng kiến thức bên ngoài evidence; không bịa số hiệu, Điều, Khoản, mức tiền, ngày hiệu lực hoặc citation.
Có thể search nhiều lần hoặc lấy một document cụ thể nếu evidence chưa đủ.
Nếu không đủ căn cứ, phải trả đúng: "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận."
Phân biệt "Quy định pháp luật" và "Suy luận theo tình huống" nếu có suy luận.
Chỉ dùng cited_document_ids xuất hiện trong evidence của lượt chạy này.
Với người lao động đồng thời có nhiều hợp đồng: không nói mỗi công ty đều đóng toàn bộ BHXH/BHYT/BHTN. Phải phân biệt hợp đồng làm căn cứ đóng BHXH, BHYT, BHTN và bảo hiểm tai nạn lao động, bệnh nghề nghiệp theo đúng evidence.
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


def _reject_unsupported_multiple_contract_claim(query: str, result: dict[str, Any]) -> dict[str, Any]:
    """Fail closed on the known high-risk multi-contract insurance claim."""
    if result.get("status") != "verified":
        return result
    routing_query = normalize_for_routing(query)
    answer = normalize_for_routing(str(result.get("answer", "")))
    asks_multiple = any(term in routing_query for term in ("hai cong ty", "2 cong ty", "nhieu hop dong", "hai hop dong"))
    claims_all_insurance = "moi cong ty" in answer and any(
        term in answer for term in ("dong bao hiem xa hoi", "dong bhxh", "dong toan bo bao hiem")
    )
    if not (asks_multiple and claims_all_insurance):
        return result
    logger.warning("Labor answer rejected for unsupported multi-contract insurance claim: query=%s", query)
    return {
        **result,
        "answer": INSUFFICIENT_EVIDENCE,
        "status": "insufficient_evidence",
        "citations": [],
        "guardrail_warnings": [
            "Câu trả lời khẳng định sai rằng mọi công ty đều đóng toàn bộ các khoản bảo hiểm; đã chặn để tránh kết luận sai."
        ],
    }


def run_labor_agent(query: str, k: int = 5, model: Any | None = None, max_steps: int = MAX_STEPS, sub_queries: list[str] | None = None) -> dict[str, Any]:
    settings = get_settings()
    cleaned_query = clean_query(query)
    clarification = clarification_for_query(cleaned_query, LABOR_DOMAIN)
    if clarification:
        return {"query": cleaned_query, "answer": clarification, "status": "needs_clarification", "citations": []}
    result = run_domain_agent(
        cleaned_query, k, settings, SPEC, search_labor_law, get_labor_document, model=model, max_steps=max_steps, sub_queries=sub_queries
    )
    return _reject_unsupported_multiple_contract_claim(cleaned_query, result)
