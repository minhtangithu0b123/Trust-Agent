"""Traffic domain adapter for the shared ReAct agent foundation."""

from __future__ import annotations

from typing import Any

from ..config import get_settings
from ..query_normalization import clean_query, expand_query_for_retrieval, normalize_for_routing
from ..retrieval import get_hybrid_retriever
from ..vectorstore import get_vectorstore
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
Nếu evidence đã có điều khoản xử phạt khớp trực tiếp với hành vi được hỏi, hãy trả lời ngay và trích dẫn đúng document_id; không search lặp lại cùng ý.
Với câu hỏi chung về nồng độ cồn, nếu evidence có nhiều ngưỡng cho đúng loại phương tiện thì phải nêu đủ các ngưỡng theo thứ tự thấp đến cao và trích dẫn đủ điều khoản tương ứng. Không trộn mức phạt giữa ô tô, mô tô/xe gắn máy và xe máy chuyên dùng.
Nếu không đủ căn cứ, phải trả đúng: "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận."
Nếu metadata hiệu lực là unknown hoặc trống, không khẳng định văn bản vẫn đang có hiệu lực; nói rõ trạng thái hiệu lực chưa được xác minh khi câu hỏi cần thông tin hiện hành.
Phân biệt "Quy định pháp luật" và "Suy luận theo tình huống" nếu có suy luận.
Chỉ dùng cited_document_ids xuất hiện trong evidence của lượt chạy này.
"""
SPEC = DomainAgentSpec(TRAFFIC_DOMAIN, "Traffic Agent", AGENT_POLICY)

def _clarification_for_ambiguous_query(query: str) -> str | None:
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
    routing = normalize_for_routing(original)
    expanded = expand_query_for_retrieval(original, routing, TRAFFIC_DOMAIN)

    # Alcohol penalties for motorcycles are three separate clauses in Article
    # 7. General similarity search can mix them with the car / specialized
    # vehicle clauses, which carry materially different fines. Fetch the exact
    # article clauses by metadata when the user names a motorcycle.
    motorcycle_terms = ("xe may", "xe mo to", "xe gan may")
    if "nong do con" in routing and any(term in routing for term in motorcycle_terms):
        store = get_vectorstore(settings, TRAFFIC_DOMAIN)
        payload = store.get(
            where={
                "$and": [
                    {"domain": TRAFFIC_DOMAIN},
                    {"so_hieu": "168/2024/NĐ-CP"},
                    {"dieu": "Điều 7"},
                ]
            },
            include=["documents", "metadatas"],
        )
        target_clauses = {"Khoản 6", "Khoản 8", "Khoản 9"}
        evidence = []
        for document_id, text, metadata in zip(
            payload.get("ids", []),
            payload.get("documents", []),
            payload.get("metadatas", []),
        ):
            metadata = metadata or {}
            source = str(metadata.get("source", ""))
            if (
                metadata.get("so_hieu") == "168/2024/NĐ-CP"
                and metadata.get("dieu") == "Điều 7"
                and metadata.get("khoan") in target_clauses
                and "Nghi-dinh-168-2024-ND-CP" in source
                and "nồng độ cồn" in str(text).casefold()
            ):
                evidence.append(compact_evidence(document_id, text or "", metadata))
        return evidence

    results = search_domain_law(settings, TRAFFIC_DOMAIN, get_hybrid_retriever, expanded, k)
    if "vuot den do" not in routing:
        return results

    # The source corpus uses the formal phrase and article number, while users
    # commonly ask with the colloquial phrase "vượt đèn đỏ".
    legal_query = (
        "Nghị định 168/2024 xe mô tô không chấp hành hiệu lệnh đèn tín hiệu "
        "giao thông Điều 7 khoản 7"
    )
    targeted = search_domain_law(settings, TRAFFIC_DOMAIN, get_hybrid_retriever, legal_query, k)
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*targeted, *results]:
        document_id = item.get("document_id")
        if document_id and document_id not in seen:
            seen.add(document_id)
            merged.append(item)
        if len(merged) >= k:
            break
    return merged


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
    routing = normalize_for_routing(cleaned_query)
    motorcycle_terms = ("xe may", "xe mo to", "xe gan may")
    if "nong do con" in routing and any(term in routing for term in motorcycle_terms):
        # The adapter already retrieves the three exact motorcycle clauses.
        # Router-generated subqueries may pull matching car/special-vehicle
        # amounts and cause the model to combine incompatible penalty tables.
        sub_queries = None
    return run_domain_agent(
        cleaned_query, k, settings, SPEC, search_traffic_law, get_traffic_document, model=model, max_steps=max_steps, sub_queries=sub_queries
    )
