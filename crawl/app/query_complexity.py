"""Cheap, deterministic decision policy for optional cross-encoder reranking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from .query_facets import extract_query_facets
from .query_normalization import normalize_for_routing


@dataclass(frozen=True)
class ComplexityDecision:
    score: int
    should_rerank: bool
    reasons: tuple[str, ...]


def assess_query_complexity(query: str, domain: str, results: Sequence[object] = ()) -> ComplexityDecision:
    """Decide whether a query needs cross-encoder precision.

    The policy uses query constraints and the initial RRF confidence. It does
    not call an LLM and therefore adds no provider latency or API cost.
    """
    routing = normalize_for_routing(query)
    score = 0
    reasons: list[str] = []
    facets = extract_query_facets(query, domain)

    if len(routing.split()) > 12:
        score += 1
        reasons.append("long_query")
    if facets.required_phrases:
        score += 2
        reasons.append("entity_constraint")
    if facets.topic_phrases:
        score += min(2, len(facets.topic_phrases))
        reasons.append("topic_constraint")
    if re.search(r"\d|/\d{4}|\b(dieu|khoan)\b", routing):
        score += 2
        reasons.append("legal_or_numeric_reference")
    if any(term in routing for term in ("muc phat", "bao nhieu", "toi da", "phan tram", "muc nao")):
        score += 1
        reasons.append("quantitative_question")
    if any(term in routing for term in (" va ", " hoac ", " neu ", " trong truong hop ")):
        score += 1
        reasons.append("multiple_conditions")

    if len(results) >= 2:
        scores = sorted(
            (float(getattr(item, "fused_score", 0.0)) for item in results),
            reverse=True,
        )
        top, second = scores[0], scores[1]
        relative_gap = (top - second) / max(abs(top), 0.001)
        if relative_gap < 0.15:
            score += 2
            reasons.append("low_rrf_separation")

    return ComplexityDecision(
        score,
        score >= 3 or "low_rrf_separation" in reasons,
        tuple(reasons),
    )
