"""Optional local cross-encoder reranking for hybrid retrieval.

The module is deliberately lazy: importing the API never downloads a model.
RRF remains the default and is also the fallback when reranking is disabled
or the model cannot be loaded.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from .config import Settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _load_cross_encoder(model_name: str, device: str) -> Any:
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device=device)


def rerank(
    query: str,
    results: list[Any],
    settings: Settings,
    enabled: bool | None = None,
) -> list[Any]:
    """Rerank hybrid candidates, returning the original result objects.

    Errors intentionally fall back to the RRF ordering. A retrieval request
    must not fail only because an optional local model is unavailable.
    """
    use_reranker = (
        getattr(settings, "reranker_enabled", False)
        if enabled is None
        else enabled
    )
    if not use_reranker or len(results) < 2:
        return results

    model_name = getattr(settings, "reranker_model", "BAAI/bge-reranker-v2-m3")
    device = getattr(settings, "embedding_device", "cpu")
    try:
        model = _load_cross_encoder(model_name, device)
        pairs = [(query, item.document.page_content) for item in results]
        batch_size = max(1, int(getattr(settings, "reranker_batch_size", 8)))
        max_length = max(32, int(getattr(settings, "reranker_max_length", 256)))
        try:
            predictions = model.predict(
                pairs,
                batch_size=batch_size,
                max_length=max_length,
                show_progress_bar=False,
            )
        except TypeError:
            # Keep compatibility with lightweight test doubles and older
            # sentence-transformers versions that accept only pairs.
            predictions = model.predict(pairs)
        raw_scores = [float(score) for score in predictions]
        if not raw_scores:
            return results

        # Blend normalized cross-encoder relevance with RRF. This preserves a
        # little of the stable sparse/dense signal and avoids score spikes.
        lo, hi = min(raw_scores), max(raw_scores)
        span = hi - lo
        normalized = [0.5 if span == 0 else (score - lo) / span for score in raw_scores]
        rrf_scores = [float(item.fused_score) for item in results]
        rlo, rhi = min(rrf_scores), max(rrf_scores)
        rspan = rhi - rlo
        normalized_rrf = [0.5 if rspan == 0 else (score - rlo) / rspan for score in rrf_scores]
        for item, cross_score, rrf_score in zip(results, normalized, normalized_rrf):
            item.fused_score = 0.75 * cross_score + 0.25 * rrf_score
        return sorted(
            results,
            key=lambda item: (
                -item.fused_score,
                str(item.document.metadata.get("id", "")),
            ),
        )
    except Exception as exc:  # pragma: no cover - exercised with an installed model
        logger.warning("Reranker unavailable; keeping RRF ranking: %s", exc)
        return results
