from __future__ import annotations

import logging
import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from ..answering import citation_from_metadata
from ..citation_guardrail import verify_citations_guardrail
from ..config import Settings
from ..llm import ModelConfigurationError, build_structured_model
from ..vectorstore import get_vectorstore
from ..retrieval import get_hybrid_retriever

logger = logging.getLogger(__name__)
INSUFFICIENT_EVIDENCE = "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận."
MAX_STEPS = 5


class AgentProviderError(RuntimeError):
    pass


class ToolDecision(BaseModel):
    action: Literal["search", "get_document", "final"]
    query: str = ""
    document_id: str = ""
    answer: str = ""
    cited_document_ids: list[str] = Field(default_factory=list)


class AgentFinalOutput(BaseModel):
    answer: str = Field(min_length=1)
    cited_document_ids: list[str] = Field(default_factory=list)


class DomainAgentState(TypedDict, total=False):
    query: str
    k: int
    max_steps: int
    settings: Any
    evidence: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    decision: dict[str, Any]
    steps: int
    answer: str
    cited_document_ids: list[str]
    status: str
    guardrail_warnings: list[str]


@dataclass(frozen=True)
class DomainAgentSpec:
    domain: str
    agent_name: str
    policy: str
    insufficient_answer: str = INSUFFICIENT_EVIDENCE


def compact_evidence(document_id: str, text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    safe_metadata = dict(metadata)
    safe_metadata["id"] = document_id
    return {
        "document_id": document_id,
        "text": text,
        "metadata": safe_metadata,
        "citation": citation_from_metadata(safe_metadata),
    }


def search_domain_law(settings: Settings, domain: str, retriever: Any, query: str, k: int, sub_queries: list[str] | None = None) -> list[dict[str, Any]]:
    ret = retriever(settings, domain=domain)
    queries_to_run = [query]
    if sub_queries:
        for sq in sub_queries:
            if sq and sq not in queries_to_run:
                queries_to_run.append(sq)
    
    seen_ids = set()
    combined_evidence = []
    
    for q in queries_to_run:
        results = ret.search(q, k=k)
        for result in results:
            doc_id = str(result.document.metadata.get("id", ""))
            if not doc_id or doc_id in seen_ids:
                continue
            if result.document.metadata.get("domain") == domain:
                seen_ids.add(doc_id)
                combined_evidence.append(
                    compact_evidence(doc_id, result.document.page_content, result.document.metadata)
                )
    return combined_evidence


def get_domain_document(settings: Settings, domain: str, document_id: str) -> dict[str, Any] | None:
    store = get_vectorstore(settings, domain=domain)
    payload = store.get(
        ids=[document_id],
        where={"domain": domain},
        include=["documents", "metadatas"],
    )
    ids = payload.get("ids", [])
    if not ids:
        return None
    index = ids.index(document_id) if document_id in ids else 0
    metadata = (payload.get("metadatas") or [])[index] or {}
    text = (payload.get("documents") or [""])[index] or ""
    if metadata.get("domain") != domain:
        return None
    return compact_evidence(document_id, text, metadata)


def build_openai_model(settings: Settings):
    try:
        return build_structured_model(settings, ToolDecision)
    except ModelConfigurationError as exc:
        raise AgentProviderError(str(exc)) from exc


def _evidence_context(state: DomainAgentState) -> str:
    blocks = []
    for item in state.get("evidence", []):
        doc_id = item.get("document_id") or item.get("id", "")
        citation_info = item.get("citation") or item.get("metadata", {})
        text = item.get("text", "")
        blocks.append(f"DOCUMENT_ID: {doc_id}\nCITATION: {citation_info}\nTEXT: {text}")
    return "\n\n--- OBSERVED EVIDENCE ---\n\n".join(blocks) or "Chưa có evidence."


def _decide_node(state: DomainAgentState, model: Any, spec: DomainAgentSpec) -> dict[str, Any]:
    steps = state.get("steps", 0) + 1
    max_steps = state.get("max_steps", MAX_STEPS)
    if steps > max_steps:
        return {"steps": steps, "decision": {"action": "final", "answer": spec.insufficient_answer}}
    prompt = (
        f"{spec.policy}\n\nCâu hỏi gốc: {state['query']}\n"
        f"Số bước đã dùng: {steps}/{max_steps}\nEvidence quan sát được:\n{_evidence_context(state)}\n\n"
        "Chọn action search, get_document hoặc final. Với search điền query; với get_document điền document_id. "
        "Với final điền answer và cited_document_ids. Nếu chưa có evidence, không được chọn final."
    )
    try:
        decision = model.invoke(prompt)
        parsed = decision if isinstance(decision, ToolDecision) else ToolDecision.model_validate(decision)
    except Exception as exc:
        raise AgentProviderError(f"{spec.agent_name} decision failed: {exc}") from exc
    if not state.get("evidence") and parsed.action == "final":
        parsed = ToolDecision(action="search", query=state["query"])
    return {"steps": steps, "decision": parsed.model_dump()}


def _execute_tool_node(
    state: DomainAgentState,
    spec: DomainAgentSpec,
    search_tool: Callable[[str, int], list[dict[str, Any]]],
    document_tool: Callable[[str], dict[str, Any] | None],
) -> dict[str, Any]:
    decision = state.get("decision", {})
    action = decision.get("action")
    if action == "search":
        tool_name = f"search_{spec.domain}_law"
        result: Any = search_tool(decision.get("query") or state["query"], state.get("k", 5))
    elif action == "get_document":
        tool_name = f"get_{spec.domain}_document"
        result = document_tool(decision.get("document_id", ""))
    else:
        return {}
    additions = result if isinstance(result, list) else ([result] if result else [])
    existing = {
        (item.get("document_id") or item.get("id"))
        for item in state.get("evidence", [])
        if (item.get("document_id") or item.get("id"))
    }
    evidence = list(state.get("evidence", []))
    evidence.extend(
        item for item in additions
        if item and (item.get("document_id") or item.get("id")) not in existing
    )
    return {"evidence": evidence, "observations": [*state.get("observations", []), {"tool": tool_name, "result": result}]}


def _route_after_decision(state: DomainAgentState) -> str:
    return "execute_tool" if state.get("decision", {}).get("action") in {"search", "get_document"} else "finalize"


def _finalize_node(state: DomainAgentState, spec: DomainAgentSpec) -> dict[str, Any]:
    decision = state.get("decision", {})
    answer = str(decision.get("answer") or spec.insufficient_answer).strip()
    if spec.insufficient_answer in answer:
        return {"answer": spec.insufficient_answer, "cited_document_ids": [], "status": "insufficient_evidence", "guardrail_warnings": []}
    observed_ids = {
        (item.get("document_id") or item.get("id"))
        for item in state.get("evidence", [])
        if (item.get("document_id") or item.get("id"))
    }
    cited_ids = list(dict.fromkeys(decision.get("cited_document_ids") or []))
    if not cited_ids or any(document_id not in observed_ids for document_id in cited_ids):
        return {"answer": spec.insufficient_answer, "cited_document_ids": [], "status": "insufficient_evidence", "guardrail_warnings": []}

    guardrail_result = verify_citations_guardrail(
        answer=answer,
        evidence=state.get("evidence", []),
        cited_document_ids=cited_ids,
        require_cited_ids=True,
        verify_quantitative_claims=True,
    )
    if guardrail_result.status != "verified":
        logger.warning("%s citation guardrail downgraded status: %s", spec.agent_name, guardrail_result.warnings)
        return {
            "answer": guardrail_result.verified_answer,
            "cited_document_ids": [],
            "status": guardrail_result.status,
            "guardrail_warnings": guardrail_result.warnings,
        }

    final = AgentFinalOutput(answer=guardrail_result.verified_answer, cited_document_ids=cited_ids)
    return {
        "answer": final.answer,
        "cited_document_ids": final.cited_document_ids,
        "status": "verified",
        "guardrail_warnings": [],
    }



def build_domain_agent_graph(
    spec: DomainAgentSpec,
    model: Any,
    search_tool: Callable[[str, int], list[dict[str, Any]]],
    document_tool: Callable[[str], dict[str, Any] | None],
):
    graph = StateGraph(DomainAgentState)
    graph.add_node("decide", lambda state: _decide_node(state, model, spec))
    graph.add_node("execute_tool", lambda state: _execute_tool_node(state, spec, search_tool, document_tool))
    graph.add_node("finalize", lambda state: _finalize_node(state, spec))
    graph.add_edge(START, "decide")
    graph.add_conditional_edges("decide", _route_after_decision)
    graph.add_edge("execute_tool", "decide")
    graph.add_edge("finalize", END)
    return graph.compile()


def run_domain_agent(
    query: str,
    k: int,
    settings: Settings,
    spec: DomainAgentSpec,
    search_tool: Callable[[str, int], list[dict[str, Any]]],
    document_tool: Callable[[str], dict[str, Any] | None],
    model: Any | None = None,
    max_steps: int = MAX_STEPS,
    sub_queries: list[str] | None = None,
) -> dict[str, Any]:
    try:
        selected_model = model or build_openai_model(settings)
        # Seed the agent with the domain adapter's retrieval path so its
        # deterministic, domain-specific expansions are applied before the
        # LLM decides whether another search is needed.
        try:
            initial_evidence = search_tool(query, k)
        except Exception:
            logger.exception("%s initial evidence search failed", spec.agent_name)
            initial_evidence = []
        if sub_queries:
            try:
                extra_evidence = search_domain_law(
                    settings,
                    spec.domain,
                    get_hybrid_retriever,
                    query,
                    k,
                    sub_queries=sub_queries,
                )
                observed_ids = {
                    item.get("document_id") or item.get("id")
                    for item in initial_evidence
                    if item.get("document_id") or item.get("id")
                }
                initial_evidence.extend(
                    item
                    for item in extra_evidence
                    if (item.get("document_id") or item.get("id")) not in observed_ids
                )
            except Exception:
                logger.exception("%s sub-query evidence search failed", spec.agent_name)
        output = build_domain_agent_graph(spec, selected_model, search_tool, document_tool).invoke(
            {"query": query, "k": k, "max_steps": max_steps, "settings": settings, "evidence": initial_evidence, "observations": [], "steps": 0},
            config={"recursion_limit": max_steps * 3 + 3},
        )
        cited_ids = output.get("cited_document_ids", [])
        evidence_by_id = {
            (item.get("document_id") or item.get("id")): item
            for item in output.get("evidence", [])
            if item.get("document_id") or item.get("id")
        }
        citations = []
        for doc_id in cited_ids:
            evidence_item = evidence_by_id.get(doc_id)
            if evidence_item is None:
                continue
            citation = dict(
                evidence_item.get("citation")
                or citation_from_metadata(evidence_item.get("metadata", evidence_item))
            )
            evidence_text = evidence_item.get("text")
            if evidence_text:
                citation["text_sha256"] = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
            citations.append(citation)
        if output.get("status") != "verified":
            citations = []
        res = {"query": query, "answer": output.get("answer", spec.insufficient_answer), "status": output.get("status", "insufficient_evidence"), "citations": citations}
        if output.get("guardrail_warnings"):
            res["guardrail_warnings"] = output["guardrail_warnings"]
        return res
    except AgentProviderError as exc:
        logger.warning("%s unavailable: %s", spec.agent_name, exc)
        return {"query": query, "answer": f"{spec.agent_name} chưa thể tạo câu trả lời vì provider chưa được cấu hình hoặc đang gặp lỗi.", "status": "provider_error", "citations": []}
    except Exception:
        logger.exception("%s execution failed", spec.agent_name)
        return {"query": query, "answer": spec.insufficient_answer, "status": "insufficient_evidence", "citations": []}


