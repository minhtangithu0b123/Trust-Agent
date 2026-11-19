"""Traffic domain adapter for the shared ReAct agent foundation."""

from __future__ import annotations

import logging
from typing import Any
import re

from ..config import get_settings
from ..clarification import clarification_for_query
from ..query_normalization import clean_query, normalize_for_routing
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
logger = logging.getLogger(__name__)
AGENT_POLICY = """Bạn là ReAct Traffic Agent chuyên tra cứu pháp luật giao thông Việt Nam.
Luôn gọi evidence trước khi trả lời và chỉ sử dụng công cụ traffic được cung cấp.
Không dùng kiến thức bên ngoài evidence; không bịa số hiệu, Điều, Khoản, mức phạt, ngày hiệu lực hoặc citation.
Có thể search nhiều lần hoặc lấy một document cụ thể nếu evidence chưa đủ.
Nếu evidence đã có điều khoản xử phạt khớp trực tiếp với hành vi được hỏi, hãy trả lời ngay và trích dẫn đúng document_id; không search lặp lại cùng ý.
Với câu hỏi vượt đèn đỏ/không chấp hành đèn tín hiệu: ô tô phải đối chiếu mức phạt ở Điều 6 Khoản 9 và nhánh trừ điểm tương ứng ở Điều 6 Khoản 16 điểm b (04 điểm); xe máy phải đối chiếu Điều 7 Khoản 7 và Điều 7 Khoản 13 điểm b (04 điểm). Không lấy nhánh nồng độ cồn (Điều 6 Khoản 9 điểm a, 10 điểm) hoặc nhánh lỗi khác để trả lời đèn đỏ. Nếu evidence không nêu rõ nhánh tương ứng, trả lời chưa đủ căn cứ thay vì suy đoán.
Khi câu hỏi nêu rõ loại phương tiện, tuyệt đối không trộn mức phạt hoặc điểm của loại phương tiện khác.
Với lỗi không đội mũ bảo hiểm trên xe mô tô/xe gắn máy, chỉ dùng Điều 7 Khoản 2 của Nghị định 168/2024/NĐ-CP khi evidence xác nhận đúng hành vi. Không tự thêm Điều 12 Khoản 5 hoặc điều khoản không xuất hiện trong evidence.
Nếu không đủ căn cứ, phải trả đúng: "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận."
Phân biệt "Quy định pháp luật" và "Suy luận theo tình huống" nếu có suy luận.
Chỉ dùng cited_document_ids xuất hiện trong evidence của lượt chạy này.
"""
SPEC = DomainAgentSpec(TRAFFIC_DOMAIN, "Traffic Agent", AGENT_POLICY)


def _is_passenger_helmet_query(routing_query: str) -> bool:
    return any(term in routing_query for term in (
        "nguoi duoc cho", "nguoi ngoi tren xe", "cho nguoi",
    ))


def _has_article(citations: list[dict[str, Any]], article_number: str) -> bool:
    needle = f"dieu {article_number}"
    return any(needle in normalize_for_routing(str(item.get("dieu", ""))) for item in citations)


def _remove_article_12_citation(answer: str) -> str:
    """Remove the passenger-only citation while preserving the driver answer."""
    article_12 = r"\u0110i\u1ec1u\s*12(?:\s*Kho\u1ea3n\s*\d+)?(?:\s*\u0111i\u1ec3m\s*[a-z])?"
    answer = re.sub(rf"{article_12}\s*(?:v\u00e0\s*)?", "", answer, flags=re.IGNORECASE)
    answer = re.sub(rf"\s*v\u00e0\s*{article_12}", "", answer, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", answer).strip()


def _reject_inconsistent_red_light_answer(query: str, result: dict[str, Any]) -> dict[str, Any]:
    """Reject a quantitatively valid but vehicle/violation-inconsistent answer.

    The citation guardrail can confirm that ``10 điểm`` exists somewhere in
    the same article, but that value belongs to the alcohol branch, not the
    red-light branch. This final domain check prevents that cross-branch
    leakage from reaching the user.
    """
    if result.get("status") != "verified":
        return result
    routing_query = normalize_for_routing(query)
    routing_answer = normalize_for_routing(str(result.get("answer", "")))
    is_helmet_query = "mu bao hiem" in routing_query or "doi mu" in routing_query
    if is_helmet_query and "dieu 12" in routing_answer and not _is_passenger_helmet_query(routing_query):
        citations = result.get("citations") or []
        if _has_article(citations, "7"):
            cleaned_answer = _remove_article_12_citation(str(result.get("answer", "")))
            filtered_citations = [
                citation for citation in citations
                if "dieu 7" in normalize_for_routing(str(citation.get("dieu", "")))
            ]
            logger.warning("Traffic helmet answer normalized from passenger Article 12 to driver Article 7: query=%s", query)
            return {
                **result,
                "answer": cleaned_answer,
                "citations": filtered_citations or citations,
                "guardrail_warnings": [
                    "Đã loại citation Điều 12 vì câu hỏi thuộc nhánh người điều khiển; giữ căn cứ Điều 7."
                ],
            }
        logger.warning("Traffic helmet answer rejected for unsupported Article 12 citation: query=%s", query)
        return {
            **result,
            "answer": INSUFFICIENT_EVIDENCE,
            "status": "insufficient_evidence",
            "citations": [],
            "guardrail_warnings": [
                "Câu trả lời chứa điều khoản không có trong evidence; đã chặn để tránh citation sai."
            ],
        }
    if "vuot den do" not in routing_query and "den tin hieu" not in routing_query:
        return result

    is_car = any(term in routing_query for term in ("o to", "oto", "xe hoi"))
    is_motorbike = any(term in routing_query for term in ("xe may", "xe mo to", "xe gan may"))
    wrong_point = (is_car and "10 diem" in routing_answer) or (is_motorbike and "06 diem" in routing_answer)
    wrong_fine = (
        (is_car and re.search(r"400\.?000.{0,20}600\.?000", routing_answer))
        or (is_motorbike and re.search(r"18\.?000\.?000.{0,20}20\.?000\.?000", routing_answer))
    )
    if not (wrong_point or wrong_fine):
        return result
    logger.warning("Traffic answer rejected for vehicle/violation mismatch: query=%s", query)
    return {
        **result,
        "answer": INSUFFICIENT_EVIDENCE,
        "status": "insufficient_evidence",
        "citations": [],
        "guardrail_warnings": [
            "Câu trả lời có dấu hiệu trộn nhánh phương tiện hoặc hành vi; đã chặn để tránh kết luận sai."
        ],
    }

def _clarification_for_ambiguous_query(query: str) -> str | None:
    domain_clarification = clarification_for_query(query, TRAFFIC_DOMAIN)
    if domain_clarification:
        return domain_clarification
    routing = normalize_for_routing(query)
    helmet_terms = ("mu bao hiem", "doi mu", "doi non")
    vehicle_terms = (
        "xe may", "xe mo to", "xe gan may", "xe dap may", "xe dap dien",
        "o to", "oto", "xe hoi", "xe dap",
    )
    if any(term in routing for term in helmet_terms) and not any(term in routing for term in vehicle_terms):
        return "Bạn muốn tra cứu loại phương tiện nào: xe máy, xe đạp máy hay ô tô?"
    return None


def search_traffic_law(query: str, k: int = 5) -> list[dict[str, Any]]:
    settings = get_settings()
    original = clean_query(query)
    # The retriever expands only the semantic/BM25 query. Pass the original
    # query here so self-query metadata planning can preserve vehicle type.
    return search_domain_law(settings, TRAFFIC_DOMAIN, get_hybrid_retriever, original, k)


def get_traffic_document(document_id: str) -> dict[str, Any] | None:
    return get_domain_document(get_settings(), TRAFFIC_DOMAIN, document_id)


def _build_model(settings):
    return build_openai_model(settings)


def build_traffic_agent_graph(model: Any):
    return build_domain_agent_graph(SPEC, model, search_traffic_law, get_traffic_document)


def run_traffic_agent(query: str, k: int = 5, model: Any | None = None, max_steps: int = MAX_STEPS, sub_queries: list[str] | None = None) -> dict[str, Any]:
    cleaned_query = clean_query(query)
    clarification = _clarification_for_ambiguous_query(cleaned_query)
    if clarification:
        return {
            "query": cleaned_query,
            "answer": clarification,
            "status": "needs_clarification",
            "citations": [],
        }
    settings = get_settings()
    result = run_domain_agent(
        cleaned_query, k, settings, SPEC, search_traffic_law, get_traffic_document, model=model, max_steps=max_steps, sub_queries=sub_queries
    )
    return _reject_inconsistent_red_light_answer(cleaned_query, result)
