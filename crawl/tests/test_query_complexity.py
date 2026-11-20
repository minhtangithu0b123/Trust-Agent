from types import SimpleNamespace

from app.query_complexity import assess_query_complexity


def test_simple_overview_does_not_need_reranker():
    decision = assess_query_complexity("Luật lao động có gì?", "labor")
    assert decision.should_rerank is False


def test_constrained_trial_period_query_needs_reranker():
    decision = assess_query_complexity(
        "Người lao động ký hợp đồng thử việc tối đa bao nhiêu ngày?", "labor"
    )
    assert decision.should_rerank is True
    assert "topic_constraint" in decision.reasons


def test_low_rrf_separation_triggers_reranker():
    results = [SimpleNamespace(fused_score=0.020), SimpleNamespace(fused_score=0.019)]
    decision = assess_query_complexity("quy định lao động", "labor", results)
    assert decision.should_rerank is True
    assert "low_rrf_separation" in decision.reasons
