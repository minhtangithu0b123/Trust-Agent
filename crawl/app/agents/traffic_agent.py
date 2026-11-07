"""Traffic domain adapter for the shared ReAct agent foundation."""

from __future__ import annotations

from typing import Any

from ..config import get_settings
from ..query_normalization import clean_query, expand_query_for_retrieval, normalize_for_routing
from ..retrieval import get_hybrid_retriever
from .base import (
    AgentFinalOutput as TrafficFinalOutput,
    AgentProviderError,
    DomainAgentSpec,
    DomainAgentState as TrafficAgentState,
    INSUFFICIENT_EVIDENCE,
    MAX_STEPS,
    ToolDecision,
    build_domain_agent_graph,
    build_openai_model,
    compact_evidence,
    get_domain_document,
    run_domain_agent,
    search_domain_law,
)

TRAFFIC_DOMAIN = "traffic"
AGENT_POLICY = """Bạn là ReAct Traffic Agent chuyên tra cứu pháp luật giao thông Việt Nam.
Luôn gọi evidence trước khi trả lời và chỉ sử dụng công cụ traffic được cung cấp.
Không dùng kiến thức bên ngoài evidence; không bịa số hiệu, Điều, Khoản, mức phạt, ngày hiệu lực hoặc citation.
Có thể search nhiều lần hoặc lấy một document cụ thể nếu evidence chưa đủ.
Nếu không đủ căn cứ, phải trả đúng: "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận."
Phân biệt "Quy định pháp luật" và "Suy luận theo tình huống" nếu có suy luận.
Chỉ dùng cited_document_ids xuất hiện trong evidence của lượt chạy này.
"""
SPEC = DomainAgentSpec(TRAFFIC_DOMAIN, "Traffic Agent", AGENT_POLICY)


def search_traffic_law(query: str, k: int = 5) -> list[dict[str, Any]]:
    settings = get_settings()
    original = clean_query(query)
    expanded = expand_query_for_retrieval(original, normalize_for_routing(original), TRAFFIC_DOMAIN)
    return search_domain_law(settings, TRAFFIC_DOMAIN, get_hybrid_retriever, expanded, k)


def get_traffic_document(document_id: str) -> dict[str, Any] | None:
    return get_domain_document(get_settings(), TRAFFIC_DOMAIN, document_id)


def _build_model(settings):
    return build_openai_model(settings)


def build_traffic_agent_graph(model: Any):
    return build_domain_agent_graph(SPEC, model, search_traffic_law, get_traffic_document)


def run_traffic_agent(query: str, k: int = 5, model: Any | None = None, max_steps: int = MAX_STEPS) -> dict[str, Any]:
    settings = get_settings()
    cleaned_query = clean_query(query)
    return run_domain_agent(
        cleaned_query, k, settings, SPEC, search_traffic_law, get_traffic_document, model=model, max_steps=max_steps
    )
