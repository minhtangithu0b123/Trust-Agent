"""Labor domain adapter for the shared ReAct agent foundation."""

from __future__ import annotations

from typing import Any

from ..config import get_settings
from ..query_normalization import clean_query, expand_query_for_retrieval, normalize_for_routing
from ..retrieval import get_hybrid_retriever
from ..vectorstore import get_vectorstore
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
    compact_evidence,
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
Khi được hỏi danh sách nội dung bắt buộc của hợp đồng lao động, phải đối chiếu đầy đủ các điểm a, b, c, d, đ, e, g, h, i, k tại khoản 1 Điều 21; không thêm nội dung từ điều khác và phải trích dẫn các evidence tương ứng.
Khi được hỏi các thời gian không được xử lý kỷ luật lao động, chỉ dùng khoản 4 và khoản 5 Điều 122; không đưa các điều cấm khác vào câu trả lời này.
Nếu không đủ căn cứ, phải trả đúng: "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận."
Nếu metadata hiệu lực là unknown hoặc trống, không khẳng định văn bản vẫn đang có hiệu lực; nói rõ trạng thái hiệu lực chưa được xác minh khi câu hỏi cần thông tin hiện hành.
Phân biệt "Quy định pháp luật" và "Suy luận theo tình huống" nếu có suy luận.
Chỉ dùng cited_document_ids xuất hiện trong evidence của lượt chạy này.
"""
SPEC = DomainAgentSpec(LABOR_DOMAIN, "Labor Agent", AGENT_POLICY)

CONTRACT_CONTENT_POINTS = ("a)", "b)", "c)", "d)", "đ)", "e)", "g)", "h)", "i)", "k)")
DISCIPLINE_PERIOD_POINTS = ("a)", "b)", "c)", "d)")


def _article_clause_evidence(settings, article: str, points: tuple[str, ...]) -> list[dict[str, Any]]:
    store = get_vectorstore(settings, LABOR_DOMAIN)
    payload = store.get(
        where={"$and": [{"domain": LABOR_DOMAIN}, {"so_hieu": "45/2019/QH14"}, {"dieu": article}]},
        include=["documents", "metadatas"],
    )
    by_point: dict[str, dict[str, Any]] = {}
    for document_id, text, metadata in zip(
        payload.get("ids", []), payload.get("documents", []), payload.get("metadatas", [])
    ):
        metadata = metadata or {}
        clause = str(metadata.get("khoan", ""))
        point = next((item for item in points if clause.startswith(f"Khoản {item}")), None)
        if not point:
            continue
        by_point[point] = compact_evidence(document_id, text or "", metadata)
    return [by_point[point] for point in points if point in by_point]


def _answer_from_article_evidence(query: str, evidence: list[dict[str, Any]], points: tuple[str, ...], article: str) -> dict[str, Any] | None:
    if len(evidence) != len(points):
        return None
    lines = []
    for item in evidence:
        clause = str(item["metadata"].get("khoan", ""))
        point = next(point for point in points if clause.startswith(f"Khoản {point}"))
        text = str(item.get("text", ""))
        content = text.split("Nội dung:", 1)[-1].strip()
        content = content.removeprefix(point).strip()
        lines.append(f"- Điểm {point} {content}")
    answer = f"Theo khoản 1 {article} Bộ luật Lao động 2019, các nội dung gồm:\n" + "\n".join(lines)
    return {
        "query": query,
        "answer": answer,
        "status": "verified",
        "citations": [item["citation"] for item in evidence],
    }


def _contract_contents_answer(query: str, settings) -> dict[str, Any] | None:
    evidence = _article_clause_evidence(settings, "Điều 21", CONTRACT_CONTENT_POINTS)
    return _answer_from_article_evidence(query, evidence, CONTRACT_CONTENT_POINTS, "Điều 21")


def _discipline_period_answer(query: str, settings) -> dict[str, Any] | None:
    # Article 122(4) enumerates the protected periods; Article 122(5) covers
    # incapacity caused by mental illness. Keep this answer scoped to those
    # provisions and avoid unrelated disciplinary prohibitions.
    evidence = _article_clause_evidence(settings, "Điều 122", (*DISCIPLINE_PERIOD_POINTS, "5."))
    if len(evidence) != len(DISCIPLINE_PERIOD_POINTS) + 1:
        return None
    answer = (
        "Theo khoản 4 và khoản 5 Điều 122 Bộ luật Lao động 2019, không xử lý kỷ luật lao động: "
        + " ".join(str(item.get("text", "")).split("Nội dung:", 1)[-1].strip() for item in evidence)
    )
    return {
        "query": query,
        "answer": answer,
        "status": "verified",
        "citations": [item["citation"] for item in evidence],
    }


def search_labor_law(query: str, k: int = 5) -> list[dict[str, Any]]:
    settings = get_settings()
    original = clean_query(query)
    routing_query = normalize_for_routing(original)
    expanded = expand_query_for_retrieval(original, routing_query, LABOR_DOMAIN)

    # High-value labor questions often need several adjacent statutory chunks.
    # The corpus stores each clause as a separate document, so searching only
    # the article heading can miss the clause that contains the actual limits.
    sub_queries: list[str] = []
    if "nghi hang nam" in routing_query:
        sub_queries.extend(
            [
                "Điều 113 điểm a nghỉ hằng năm 12 ngày làm việc điều kiện bình thường",
                "Điều 113 điểm b nghỉ hằng năm 14 ngày làm việc người chưa thành niên khuyết tật",
                "Điều 113 điểm c nghỉ hằng năm 16 ngày làm việc công việc nặng nhọc độc hại nguy hiểm",
            ]
        )
    if "don phuong cham dut hop dong" in routing_query and (
        "nguoi lao dong" in routing_query or "nhan vien" in routing_query
    ):
        sub_queries.append(
            "Điều 35 khoản 1 thời hạn người lao động báo trước: 45 ngày, 30 ngày, 03 ngày"
        )

    # The labor corpus is clause-level. Seed all relevant parts for questions
    # whose answers depend on multiple clauses, so the model does not invent a
    # short summary from only the article heading or first clause.
    if any(term in routing_query for term in ("ky han tra luong", "tra cham", "thoi diem tra luong")):
        sub_queries.extend(
            [
                "Điều 94 khoản 1 người sử dụng lao động trả lương trực tiếp đầy đủ đúng hạn",
                "Điều 97 khoản 1 trả lương theo giờ ngày tuần không quá 15 ngày",
                "Điều 97 khoản 2 trả lương theo tháng một tháng một lần hoặc nửa tháng một lần thời điểm chu kỳ",
                "Điều 97 khoản 4 bất khả kháng trả lương chậm không quá 30 ngày lãi chậm trả từ 15 ngày",
            ]
        )
    if "hop dong lao dong" in routing_query and any(
        term in routing_query for term in ("noi dung", "gom nhung gi", "can co gi")
    ):
        sub_queries.extend(
            [
                "Điều 21 nội dung chủ yếu hợp đồng lao động khoản 1",
                "Điều 21 điểm a tên địa chỉ người sử dụng lao động người giao kết",
                "Điều 21 điểm b thông tin người lao động ngày sinh giới tính nơi cư trú căn cước",
                "Điều 21 điểm c công việc địa điểm làm việc",
                "Điều 21 điểm d thời hạn hợp đồng lao động",
                "Điều 21 điểm đ mức lương hình thức thời hạn trả lương phụ cấp",
                "Điều 21 điểm e chế độ nâng bậc nâng lương",
                "Điều 21 điểm g thời giờ làm việc nghỉ ngơi",
                "Điều 21 điểm h trang bị bảo hộ lao động",
                "Điều 21 điểm i bảo hiểm xã hội y tế thất nghiệp",
                "Điều 21 điểm k đào tạo bồi dưỡng nâng cao kỹ năng nghề",
            ]
        )
    if "ky luat lao dong" in routing_query and any(
        term in routing_query for term in ("khong duoc", "truong hop", "cam xu ly")
    ):
        sub_queries.extend(
            [
                "Điều 122 khoản 4 không được xử lý kỷ luật lao động nghỉ ốm nghỉ phép bị tạm giữ mang thai nghỉ thai sản nuôi con dưới 12 tháng",
                "Điều 127 khoản 3 cấm xử lý kỷ luật hành vi không quy định trong nội quy lao động hợp đồng hoặc pháp luật",
            ]
        )
    if "tuoi nghi huu" in routing_query:
        sub_queries.append("Điều 169 Bộ luật Lao động lộ trình tuổi nghỉ hưu năm 2026 nam nữ điều kiện bình thường")

    return search_domain_law(
        settings,
        LABOR_DOMAIN,
        get_hybrid_retriever,
        expanded,
        k,
        sub_queries=sub_queries,
    )


def get_labor_document(document_id: str) -> dict[str, Any] | None:
    return get_domain_document(get_settings(), LABOR_DOMAIN, document_id)


def _build_model(settings):
    return build_openai_model(settings)


def build_labor_agent_graph(model: Any):
    return build_domain_agent_graph(SPEC, model, search_labor_law, get_labor_document)


def run_labor_agent(query: str, k: int = 5, model: Any | None = None, max_steps: int = MAX_STEPS, sub_queries: list[str] | None = None) -> dict[str, Any]:
    settings = get_settings()
    cleaned_query = clean_query(query)
    routing_query = normalize_for_routing(cleaned_query)
    if "hop dong lao dong" in routing_query and any(
        term in routing_query for term in ("noi dung", "gom nhung gi", "can co gi")
    ):
        direct_answer = _contract_contents_answer(cleaned_query, settings)
        if direct_answer:
            return direct_answer
    if "ky luat lao dong" in routing_query and any(
        term in routing_query for term in ("khong duoc", "truong hop", "cam xu ly")
    ):
        direct_answer = _discipline_period_answer(cleaned_query, settings)
        if direct_answer:
            return direct_answer
    return run_domain_agent(
        cleaned_query, k, settings, SPEC, search_labor_law, get_labor_document, model=model, max_steps=max_steps, sub_queries=sub_queries
    )
