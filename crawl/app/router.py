import logging
import operator
import uuid
from typing import Annotated, Any, Literal
from typing_extensions import TypedDict

from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph

from .citation_guardrail import INSUFFICIENT_EVIDENCE, verify_citations_guardrail
from .intent_guardrail import get_intent_guardrail
from .agents.traffic_agent import run_traffic_agent
from .agents.labor_agent import run_labor_agent
from .agents.accounting_agent import run_accounting_agent
from .config import Settings, get_settings
from .query_normalization import clean_query, expand_query_for_retrieval, normalize_for_routing
from .llm import build_structured_model

logger = logging.getLogger(__name__)

_default_checkpointer = MemorySaver()

LEGAL_DOMAINS = ("traffic", "labor", "accounting")
DOMAIN_LABELS = {
    "traffic": "giao th\u00f4ng",
    "labor": "lao \u0111\u1ed9ng",
    "accounting": "thu\u1ebf/k\u1ebf to\u00e1n",
}
CLARIFICATION_ANSWER = (
    "B\u1ea1n mu\u1ed1n tra c\u1ee9u l\u0129nh v\u1ef1c n\u00e0o: "
    "giao th\u00f4ng, lao \u0111\u1ed9ng hay thu\u1ebf/k\u1ebf to\u00e1n?"
)


class Classification(BaseModel):
    domain: Literal["traffic", "labor", "accounting"]
    query: str = Field(min_length=2)
    sub_queries: list[str] = Field(default_factory=list, description="Danh sách các hành vi vi phạm hoặc câu hỏi con cốt lõi được bóc tách từ tình huống dài")


class ClassificationPayload(BaseModel):
    classifications: list[Classification] = Field(default_factory=list)


class AgentOutput(BaseModel):
    domain: Literal["traffic", "labor", "accounting"]
    query: str
    answer: str
    status: str
    citations: list[dict[str, Any]] = Field(default_factory=list)


class SynthesizerPayload(BaseModel):
    answer: str = Field(
        description="Câu trả lời pháp lý tổng hợp liền mạch, chuẩn xác, mạch lạc, chia bố cục rõ ràng"
    )
    cited_document_ids: list[str] = Field(
        default_factory=list,
        description="Danh sách các document_id thực sự được viện dẫn trong câu trả lời"
    )


def _reduce_results(
    left: list[dict[str, Any]] | None,
    right: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Accumulates fan-out agent outputs like operator.add, but resets to empty
    when an empty list is sent (e.g. at the start of a new turn)."""
    if right is None:
        return left or []
    if len(right) == 0:
        return []
    return operator.add(left or [], right)


class RouterState(TypedDict, total=False):
    query: str
    original_query: str
    routing_query: str
    k: int
    classifications: list[dict[str, str]]
    classification: dict[str, str]
    results: Annotated[list[dict[str, Any]], _reduce_results]
    messages: Annotated[list[dict[str, str]], operator.add]
    thread_id: str | None
    final_answer: str
    final_citations: list[dict[str, Any]]
    status: str
    guardrail_status: str
    guardrail_warnings: list[str]


def _normalize_classifications(items: list[Classification]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        if item.domain not in LEGAL_DOMAINS or item.domain in seen:
            continue
        query = clean_query(item.query)
        if not query:
            continue
        seen.add(item.domain)
        sub_qs = [clean_query(sq) for sq in getattr(item, "sub_queries", []) if clean_query(sq)]
        entry: dict[str, Any] = {"domain": item.domain, "query": query}
        if sub_qs:
            entry["sub_queries"] = sub_qs
        result.append(entry)
    return result


def _keyword_classify(
    routing_query: str,
    original_query: str | None = None,
) -> list[dict[str, str]]:
    """Classify only from routing_query; return sub-questions from original_query."""
    text = routing_query
    original = clean_query(original_query if original_query is not None else routing_query)
    keywords: dict[str, tuple[str, ...]] = {
        "traffic": (
            "giao thong", "duong bo", "xe may", "o to", "xe o to",
            "nong do con", "toc do", "bien bao", "bang lai", "giay phep lai xe",
            "tai nan", "phat giao thong", "vi pham giao thong",
        ),
        "labor": (
            "lao dong", "nguoi lao dong", "hop dong lao dong", "tien luong",
            "tien cong", "luong", "nghi phep", "nghi hang nam", "thu viec",
            "sa thai", "cham dut hop dong", "gio lam viec", "bao hiem xa hoi",
        ),
        "accounting": (
            "thue", "ke toan", "hoa don", "vat", "gtgt",
            "thu nhap ca nhan", "khau tru", "quyet toan thue", "doanh nghiep",
        ),
    }
    matched = [
        domain for domain, terms in keywords.items()
        if any(term in text for term in terms)
    ]
    return [
        {
            "domain": domain,
            "query": f"{original} (t\u1eadp trung v\u00e0o l\u0129nh v\u1ef1c {DOMAIN_LABELS[domain]})",
        }
        for domain in matched
    ]


def _classify_with_llm(
    query: str,
    settings: Settings,
    messages: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Classify using the original cleaned Vietnamese query, never routing_query."""
    provider = str(getattr(settings, "llm_provider", "openai")).strip().casefold()
    key_name = "gemini_api_key" if provider == "gemini" else "openai_api_key"
    if not getattr(settings, key_name, None):
        return []
    try:
        model = build_structured_model(settings, ClassificationPayload)
        history_context = ""
        if messages:
            recent = messages[-4:]
            formatted = "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}"
                for m in recent if isinstance(m, dict)
            )
            if formatted:
                history_context = f"L\u1ecbch s\u1eed h\u1ed9i tho\u1ea1i:\n{formatted}\n\n"
        prompt = (
            "B\u1ea1n l\u00e0 b\u1ed9 ph\u00e2n lo\u1ea1i truy v\u1ea5n ph\u00e1p lu\u1eadt Vi\u1ec7t Nam. "
            "Ch\u1ec9 ch\u1ecdn domain trong danh s\u00e1ch: traffic, labor, accounting. "
            "T\u1ea1o sub-question ti\u1ebfng Vi\u1ec7t cho t\u1eebng domain. "
            "N\u1ebfu ng\u01b0\u1eddi d\u00f9ng h\u1ecfi c\u00e2u ti\u1ebfp n\u1ed1i li\u00ean quan \u0111\u1ebfn ch\u1ee7 \u0111\u1ec1 \u1edf l\u01b0\u1ee3t tr\u01b0\u1edbc, h\u00e3y s\u1eed d\u1ee5ng ng\u1eef c\u1ea3nh l\u1ecbch s\u1eed h\u1ed9i tho\u1ea1i \u0111\u1ec3 x\u00e1c \u0111\u1ecbnh \u0111\u00fang domain. "
            "N\u1ebfu truy v\u1ea5n kh\u00f4ng \u0111\u1ee7 r\u00f5, tr\u1ea3 classifications r\u1ed7ng. "
            "Kh\u00f4ng \u0111\u01b0\u1ee3c t\u1ea1o domain kh\u00e1c.\n\n"
            f"{history_context}"
            f"Query: {query}"
        )
        payload = model.invoke(prompt)
        return _normalize_classifications(payload.classifications)
    except Exception as exc:
        logger.warning("Router classifier provider failed; using keyword fallback: %s", exc)
        return []


def _normalize_raw_classifications(items: list[dict[str, str]]) -> list[dict[str, str]]:
    models: list[Classification] = []
    for item in items:
        try:
            models.append(Classification.model_validate(item))
        except Exception:
            continue
    return _normalize_classifications(models)


def _expand_classifications(items: list[dict[str, Any]], original_query: str) -> list[dict[str, Any]]:
    routing_query = normalize_for_routing(original_query)
    expanded_items: list[dict[str, Any]] = []
    for item in items:
        expanded = expand_query_for_retrieval(original_query, routing_query, item["domain"])
        if expanded == original_query and clean_query(item["query"]) != original_query:
            expanded = clean_query(item["query"])
        sub_qs = item.get("sub_queries", [])
        entry: dict[str, Any] = {"domain": item["domain"], "query": expanded}
        if sub_qs:
            entry["sub_queries"] = sub_qs
        expanded_items.append(entry)
    return expanded_items


def _classify_query(
    query: str,
    settings: Settings,
    messages: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    original_query = clean_query(query)
    try:
        raw_items = _classify_with_llm(original_query, settings, messages=messages)
    except TypeError:
        raw_items = _classify_with_llm(original_query, settings)
    llm_items = _normalize_raw_classifications(raw_items)
    if llm_items:
        return _expand_classifications(llm_items, original_query)
    routing_query = normalize_for_routing(original_query)
    return _expand_classifications(_keyword_classify(routing_query, original_query), original_query)


def classify_query(state: RouterState) -> dict[str, Any]:
    original_query = clean_query(state.get("original_query") or state.get("query", ""))
    routing_query = normalize_for_routing(original_query)
    messages = state.get("messages", [])
    # Input Intent Guardrail: Chan chao hoi & cau hoi ngoai le (0d API)
    intent_result = get_intent_guardrail().check_intent(original_query)
    if intent_result.intent != "in_scope":
        resp_msg = intent_result.response or CLARIFICATION_ANSWER
        status_val = intent_result.intent
        return {
            "original_query": original_query,
            "routing_query": routing_query,
            "classifications": [],
            "final_answer": resp_msg,
            "final_citations": [],
            "status": status_val,
            "guardrail_status": status_val,
            "guardrail_warnings": [],
            "results": [],
            "messages": [
                {"role": "user", "content": original_query},
                {"role": "assistant", "content": resp_msg},
            ],
        }

    classifications = _classify_query(original_query, get_settings(), messages=messages)
    if not classifications:
        return {
            "original_query": original_query,
            "routing_query": routing_query,
            "classifications": [],
            "final_answer": CLARIFICATION_ANSWER,
            "final_citations": [],
            "status": "needs_clarification",
            "guardrail_status": "needs_clarification",
            "guardrail_warnings": [],
            "results": [],
            "messages": [
                {"role": "user", "content": original_query},
                {"role": "assistant", "content": CLARIFICATION_ANSWER},
            ],
        }
    return {
        "original_query": original_query,
        "routing_query": routing_query,
        "classifications": classifications,
        "status": "routing",
        "results": [],
    }


def route_to_agents(state: RouterState) -> list[Send] | str:
    classifications = state.get("classifications", [])
    if not classifications:
        return END
    sends: list[Send] = []
    for classification in classifications:
        domain = classification["domain"]
        node = {
            "traffic": "query_traffic",
            "labor": "query_labor",
            "accounting": "query_accounting",
        }.get(domain)
        if node is None:
            continue
        sends.append(Send(node, {
            "query": clean_query(classification["query"]),
            "original_query": clean_query(classification["query"]),
            "k": state.get("k", 5),
            "classification": classification,
        }))
    return sends or END


def _run_agent(
    state: RouterState,
    public_domain: str,
    agent_runner: Any,
) -> dict[str, Any]:
    classification = state.get("classification", {})
    query = clean_query(state.get("query") or classification.get("query", ""))
    k = state.get("k", 5)
    try:
        result = agent_runner(query, k)
        output = AgentOutput(
            domain=public_domain,
            query=clean_query(str(result.get("query", query))),
            answer=str(result.get("answer", INSUFFICIENT_EVIDENCE)),
            status=str(result.get("status", "insufficient_evidence")),
            citations=list(result.get("citations", [])),
        )
    except Exception:
        logger.exception("Router agent failed: %s", public_domain)
        output = AgentOutput(
            domain=public_domain,
            query=query,
            answer="Chưa thể xử lý nhánh pháp luật này.",
            status="provider_error",
            citations=[],
        )
    return {"results": [output.model_dump()]}

def query_traffic(state: RouterState) -> dict[str, Any]:
    return _run_agent(state, "traffic", run_traffic_agent)

def query_labor(state: RouterState) -> dict[str, Any]:
    return _run_agent(state, "labor", run_labor_agent)

def query_accounting(state: RouterState) -> dict[str, Any]:
    return _run_agent(state, "accounting", run_accounting_agent)


def _deduplicate_citations(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        for citation in result.get("citations", []):
            document_id = citation.get("document_id")
            key = str(document_id) if document_id is not None else repr(citation)
            if key not in seen:
                seen.add(key)
                citations.append(citation)
    return citations


SYNTHESIZER_SYSTEM_PROMPT = """Bạn là Chuyên gia Tổng hợp Pháp lý Cao cấp của Trust Agent (Việt Nam).
Nhiệm vụ của bạn là tổng hợp các kết quả tra cứu độc lập từ các nhánh chuyên môn (Giao thông, Lao động, Thuế/Kế toán) thành một câu trả lời pháp lý thống nhất, chuẩn xác, mạch lạc và có giá trị tham vấn thực tế cao.

NGUYÊN TẮC CỐT LÕI:
1. TRUNG THỰC VỚI CĂN CỨ PHÁP LÝ (GROUNDEDNESS):
   - Chỉ sử dụng các điều luật, quy định, số hiệu văn bản (Nghị định, Luật, Thông tư, Điều, Khoản) đã xuất hiện trong kết quả tra cứu của từng nhánh.
   - TUYỆT ĐỐI KHÔNG tự bịa đặt, suy đoán thêm số hiệu văn bản, điều khoản, mức phạt, mức bồi thường hoặc thời hạn ngoài dữ liệu được cung cấp.
2. TỔNG HỢP VÀ LIÊN KẾT ĐA NGÀNH:
   - Phân tích mối liên hệ, sự tương tác hoặc ràng buộc pháp lý giữa các lĩnh vực đối với tình huống của người dùng.
   - Trình bày mạch lạc, liên kết chặt chẽ các vấn đề thay vì sao chép rời rạc.
3. NGUYÊN TẮC XỬ LÝ NHÁNH THIẾU CHỨNG CỨ:
   - Nếu một nhánh chuyên môn có trạng thái "insufficient_evidence" hoặc câu trả lời chưa đủ căn cứ, nêu rõ phạm vi chưa đủ dữ liệu cho nhánh đó, không tự suy diễn thay thế.
4. CẤU TRÚC BÀI TỔNG HỢP CHUẨN:
   - Tóm tắt kết luận trực diện vào vấn đề.
   - Căn cứ & Phân tích chi tiết theo từng khía cạnh pháp luật, dẫn chiếu chính xác Điều, Khoản, Văn bản.
   - Đánh giá tổng hợp / Khuyến nghị thực thi.
5. VIỆN DẪN DOCUMENT ID:
   - Liệt kê chính xác danh sách cited_document_ids của những tài liệu pháp lý thực tế đã được viện dẫn trong câu trả lời tổng hợp."""


def _build_synthesizer_user_prompt(
    query: str,
    results: list[dict[str, Any]],
) -> str:
    domain_sections = []
    for item in results:
        domain = item.get("domain", "chung")
        domain_label = DOMAIN_LABELS.get(domain, domain)
        status = item.get("status", "unknown")
        answer = item.get("answer", "")
        citations = item.get("citations", [])

        cit_lines = []
        for c in citations:
            if isinstance(c, dict):
                doc_id = c.get("document_id") or c.get("id") or ""
                ten = c.get("ten_van_ban", "")
                so_hieu = c.get("so_hieu", "")
                dieu = c.get("dieu", "")
                khoan = c.get("khoan", "")
                cit_lines.append(f"  + [{doc_id}] {ten} - Số hiệu: {so_hieu} - {dieu} {khoan}".strip())
        cit_text = "\n".join(cit_lines) if cit_lines else "  + Không có trích dẫn cụ thể."
        domain_sections.append(
            f"=== LĨNH VỰC: {domain_label.upper()} (Trạng thái: {status}) ===\n"
            f"Nội dung tra cứu:\n{answer}\n"
            f"Căn cứ pháp lý sẵn có:\n{cit_text}"
        )
    context_str = "\n\n".join(domain_sections)
    return (
        f"Câu hỏi của người dùng:\n{query}\n\n"
        f"Kết quả tra cứu từ các nhánh chuyên môn:\n"
        f"{context_str}\n\n"
        f"Hãy tổng hợp thành câu trả lời thống nhất, mạch lạc, chuẩn xác theo đúng cấu trúc và nguyên tắc đã quy định."
    )


def _fallback_synthesize(
    query: str,
    verified_results: list[dict[str, Any]],
) -> str:
    if len(verified_results) == 1:
        return verified_results[0].get("answer", INSUFFICIENT_EVIDENCE)
    sections = []
    for item in verified_results:
        domain = item.get("domain", "")
        domain_label = DOMAIN_LABELS.get(domain, domain).capitalize()
        answer = item.get("answer", "").strip()
        sections.append(f"### Lĩnh vực {domain_label}\n{answer}")
    return "\n\n".join(sections)


def _synthesize_with_llm(
    query: str,
    verified_results: list[dict[str, Any]],
    settings: Settings,
) -> str:
    if not getattr(settings, "openai_api_key", None):
        return _fallback_synthesize(query, verified_results)
    try:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0,
        ).with_structured_output(SynthesizerPayload)
        user_prompt = _build_synthesizer_user_prompt(query, verified_results)
        payload = model.invoke([
            {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
        if hasattr(payload, "answer") and payload.answer:
            return payload.answer.strip()
        if isinstance(payload, str) and payload.strip():
            return payload.strip()
        if isinstance(payload, dict) and payload.get("answer"):
            return str(payload["answer"]).strip()
        return _fallback_synthesize(query, verified_results)
    except Exception as exc:
        logger.warning("Synthesizer LLM failed; using fallback formatting: %s", exc)
        return _fallback_synthesize(query, verified_results)


def synthesize_results(state: RouterState) -> dict[str, Any]:
    query = state.get("original_query") or state.get("query", "")
    results = state.get("results", [])
    verified = [result for result in results if result.get("status") == "verified"]
    if not verified:
        turn_messages = [
            {"role": "user", "content": query},
            {"role": "assistant", "content": INSUFFICIENT_EVIDENCE},
        ]
        return {
            "final_answer": INSUFFICIENT_EVIDENCE,
            "final_citations": [],
            "status": "insufficient_evidence",
            "guardrail_status": "insufficient_evidence",
            "guardrail_warnings": [],
            "messages": turn_messages,
        }
    if len(verified) == 1:
        raw_answer = verified[0].get("answer", INSUFFICIENT_EVIDENCE)
    else:
        raw_answer = _synthesize_with_llm(query, verified, get_settings())

    combined_citations = _deduplicate_citations(verified)
    guardrail_result = verify_citations_guardrail(
        answer=raw_answer,
        evidence=combined_citations,
    )

    if guardrail_result.status != "verified":
        final_answer = guardrail_result.verified_answer
        final_status = guardrail_result.status
        final_citations = []
        guardrail_warnings = guardrail_result.warnings
    else:
        final_answer = raw_answer
        final_status = "verified"
        final_citations = combined_citations
        guardrail_warnings = []

    turn_messages = [
        {"role": "user", "content": query},
        {"role": "assistant", "content": final_answer},
    ]
    return {
        "final_answer": final_answer,
        "final_citations": final_citations,
        "status": final_status,
        "guardrail_status": final_status,
        "guardrail_warnings": guardrail_warnings,
        "messages": turn_messages,
    }


def build_router_graph(checkpointer: Any = None):
    graph = StateGraph(RouterState)
    graph.add_node("classify_query", classify_query)
    graph.add_node("query_traffic", query_traffic)
    graph.add_node("query_labor", query_labor)
    graph.add_node("query_accounting", query_accounting)
    graph.add_node("synthesize_results", synthesize_results)
    graph.add_edge(START, "classify_query")
    graph.add_conditional_edges("classify_query", route_to_agents)
    graph.add_edge("query_traffic", "synthesize_results")
    graph.add_edge("query_labor", "synthesize_results")
    graph.add_edge("query_accounting", "synthesize_results")
    graph.add_edge("synthesize_results", END)
    return graph.compile(checkpointer=checkpointer or _default_checkpointer)


def run_router(query: str, k: int = 5, thread_id: str | None = None) -> dict[str, Any]:
    effective_thread_id = thread_id or str(uuid.uuid4())
    original_query = clean_query(query)
    state: RouterState = {
        "query": original_query,
        "original_query": original_query,
        "routing_query": normalize_for_routing(original_query),
        "k": k,
        "classifications": [],
        "results": [],
        "thread_id": effective_thread_id,
        "final_answer": "",
        "final_citations": [],
        "status": "routing",
        "guardrail_status": "",
        "guardrail_warnings": [],
    }
    config = {"configurable": {"thread_id": effective_thread_id}}
    output = build_router_graph().invoke(state, config=config)
    final_status = output.get("status", "insufficient_evidence")
    return {
        "query": output.get("original_query", original_query),
        "classifications": output.get("classifications", []),
        "results": output.get("results", []),
        "answer": output.get("final_answer", INSUFFICIENT_EVIDENCE),
        "citations": output.get("final_citations", []),
        "status": final_status,
        "guardrail_status": output.get("guardrail_status") or final_status,
        "guardrail_warnings": output.get("guardrail_warnings", []),
        "thread_id": effective_thread_id,
    }



