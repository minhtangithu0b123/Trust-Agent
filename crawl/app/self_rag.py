"""Self-RAG style evidence evaluation for the legal agents.

This module keeps the retrieve/critique decision explicit and deterministic.
The LLM remains responsible for wording, while this controller decides
whether the current evidence is sufficient to proceed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .hop_planner import plan_next_hop
from .query_normalization import normalize_for_routing


@dataclass(frozen=True)
class SelfRAGCritique:
    should_retrieve: bool
    evidence_relevant: bool
    evidence_sufficient: bool
    answer_supported: bool
    missing_aspects: tuple[str, ...] = ()
    follow_up_queries: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def critique_evidence(
    query: str,
    domain: str,
    evidence: list[dict[str, Any]],
    cited_document_ids: list[str] | None = None,
    draft: str = "",
) -> SelfRAGCritique:
    """Evaluate retrieval coverage without allowing the LLM to invent facts."""
    observed_ids = {
        str(item.get("document_id") or item.get("id"))
        for item in evidence
        if item.get("document_id") or item.get("id")
    }
    evidence_relevant = any(
        str(item.get("metadata", {}).get("domain", domain)) == domain
        for item in evidence
    )
    citation_ids = set(cited_document_ids or [])
    answer_supported = bool(draft.strip()) and bool(citation_ids) and citation_ids.issubset(observed_ids)
    plan = plan_next_hop(query, domain, evidence)
    missing = tuple(plan.missing_facets)
    follow_ups = tuple(plan.queries)
    sufficient = evidence_relevant and not missing
    return SelfRAGCritique(
        should_retrieve=not sufficient,
        evidence_relevant=evidence_relevant,
        evidence_sufficient=sufficient,
        answer_supported=answer_supported if draft else sufficient,
        missing_aspects=missing,
        follow_up_queries=follow_ups,
    )
