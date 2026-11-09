import logging
import operator
from typing import Annotated, Any, Literal
from typing_extensions import TypedDict

from pydantic import BaseModel, Field
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph

from .answering import INSUFFICIENT_EVIDENCE
from .agents.traffic_agent import run_traffic_agent
from .agents.labor_agent import run_labor_agent
from .agents.accounting_agent import run_accounting_agent
from .config import Settings, get_settings
from .query_normalization import clean_query, expand_query_for_retrieval, normalize_for_routing
from .llm import build_structured_model

logger = logging.getLogger(__name__)

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


class ClassificationPayload(BaseModel):
    classifications: list[Classification] = Field(default_factory=list)


class AgentOutput(BaseModel):
    domain: Literal["traffic", "labor", "accounting"]
    query: str
    answer: str
    status: str
    citations: list[dict[str, Any]] = Field(default_factory=list)


class RouterState(TypedDict, total=False):
    query: str
    original_query: str
    routing_query: str
    k: int
    classifications: list[dict[str, str]]
    classification: dict[str, str]
    results: Annotated[list[dict[str, Any]], operator.add]
    final_answer: str
    final_citations: list[dict[str, Any]]
    status: str


def _normalize_classifications(items: list[Classification]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for item in items:
        if item.domain not in LEGAL_DOMAINS or item.domain in seen:
            continue
        query = clean_query(item.query)
        if not query:
            continue
        seen.add(item.domain)
        result.append({"domain": item.domain, "query": query})
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


def _classify_with_llm(query: str, settings: Settings) -> list[dict[str, str]]:
    """Classify using the original cleaned Vietnamese query, never routing_query."""
    provider = str(getattr(settings, "llm_provider", "openai")).strip().casefold()
    key_name = "gemini_api_key" if provider == "gemini" else "openai_api_key"
    if not getattr(settings, key_name, None):
        return []
    try:
        model = build_structured_model(settings, ClassificationPayload)
        prompt = (
            "B\u1ea1n l\u00e0 b\u1ed9 ph\u00e2n lo\u1ea1i truy v\u1ea5n ph\u00e1p lu\u1eadt Vi\u1ec7t Nam. "
            "Ch\u1ec9 ch\u1ecdn domain trong danh s\u00e1ch: traffic, labor, accounting. "
            "T\u1ea1o sub-question ti\u1ebfng Vi\u1ec7t cho t\u1eebng domain. "
            "N\u1ebfu truy v\u1ea5n kh\u00f4ng \u0111\u1ee7 r\u00f5, tr\u1ea3 classifications r\u1ed7ng. "
            "Kh\u00f4ng \u0111\u01b0\u1ee3c t\u1ea1o domain kh\u00e1c.\n\n"
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


def _expand_classifications(items: list[dict[str, str]], original_query: str) -> list[dict[str, str]]:
    routing_query = normalize_for_routing(original_query)
    expanded_items: list[dict[str, str]] = []
    for item in items:
        expanded = expand_query_for_retrieval(original_query, routing_query, item["domain"])
        # Preserve an LLM-created sub-question when no known expansion applies.
        if expanded == original_query and clean_query(item["query"]) != original_query:
            expanded = clean_query(item["query"])
        expanded_items.append({"domain": item["domain"], "query": expanded})
    return expanded_items


def _classify_query(query: str, settings: Settings) -> list[dict[str, str]]:
    original_query = clean_query(query)
    llm_items = _normalize_raw_classifications(_classify_with_llm(original_query, settings))
    if llm_items:
        return _expand_classifications(llm_items, original_query)
    routing_query = normalize_for_routing(original_query)
    return _expand_classifications(_keyword_classify(routing_query, original_query), original_query)


def classify_query(state: RouterState) -> dict[str, Any]:
    original_query = clean_query(state.get("original_query") or state["query"])
    routing_query = normalize_for_routing(original_query)
    classifications = _classify_query(original_query, get_settings())
    if not classifications:
        return {
            "original_query": original_query,
            "routing_query": routing_query,
            "classifications": [],
            "final_answer": CLARIFICATION_ANSWER,
            "final_citations": [],
            "status": "needs_clarification",
        }
    return {
        "original_query": original_query,
        "routing_query": routing_query,
        "classifications": classifications,
        "status": "routing",
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


def synthesize_results(state: RouterState) -> dict[str, Any]:
    results = state.get("results", [])
    verified = [result for result in results if result.get("status") == "verified"]
    if not verified:
        return {
            "final_answer": INSUFFICIENT_EVIDENCE,
            "final_citations": [],
            "status": "insufficient_evidence",
        }
    if len(verified) == 1:
        answer = verified[0].get("answer", INSUFFICIENT_EVIDENCE)
    else:
        sections = [
            f"{DOMAIN_LABELS.get(result.get('domain', ''), result.get('domain', ''))}: {result.get('answer', '')}"
            for result in verified
        ]
        answer = "\n\n".join(sections)
    return {
        "final_answer": answer,
        "final_citations": _deduplicate_citations(verified),
        "status": "verified",
    }


def build_router_graph():
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
    return graph.compile()


def run_router(query: str, k: int = 5) -> dict[str, Any]:
    original_query = clean_query(query)
    state: RouterState = {
        "query": original_query,
        "original_query": original_query,
        "routing_query": normalize_for_routing(original_query),
        "k": k,
        "classifications": [],
        "results": [],
        "final_answer": "",
        "final_citations": [],
        "status": "routing",
    }
    output = build_router_graph().invoke(state)
    return {
        "query": output.get("original_query", original_query),
        "classifications": output.get("classifications", []),
        "results": output.get("results", []),
        "answer": output.get("final_answer", INSUFFICIENT_EVIDENCE),
        "citations": output.get("final_citations", []),
        "status": output.get("status", "insufficient_evidence"),
    }



