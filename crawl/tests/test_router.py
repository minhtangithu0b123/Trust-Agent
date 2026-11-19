from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.router as router
from app.main import app


def settings_without_llm():
    return SimpleNamespace(openai_api_key=None, labor_domain="labor")


def test_keyword_fallback_routes_each_domain(monkeypatch):
    monkeypatch.setattr(router, "get_settings", settings_without_llm)
    assert router._classify_query("Mức phạt nồng độ cồn khi lái xe?", settings_without_llm())[0]["domain"] == "traffic"
    assert router._classify_query("Người lao động được nghỉ hằng năm thế nào?", settings_without_llm())[0]["domain"] == "labor"
    assert router._classify_query("Cách tính thuế thu nhập cá nhân?", settings_without_llm())[0]["domain"] == "accounting"


def test_multi_domain_routing_and_reducer_keep_parallel_outputs(monkeypatch):
    monkeypatch.setattr(router, "get_settings", settings_without_llm)
    calls = []

    def fake_agent(domain):
        def run(query, k):
            calls.append(domain)
            return {
                "domain": domain,
                "answer": f"Answer for {domain}",
                "status": "verified",
                "citations": [{"document_id": "shared-doc", "dieu": "Điều 1"}],
            }
        return run

    monkeypatch.setattr(router, "run_traffic_agent", fake_agent("traffic"))
    monkeypatch.setattr(router, "run_labor_agent", fake_agent("labor"))
    monkeypatch.setattr(router, "run_accounting_agent", fake_agent("accounting"))
    result = router.run_router("quy định về giao thông, lao động và thuế", 5)
    assert {item["domain"] for item in result["classifications"]} == {"traffic", "labor", "accounting"}
    assert {item["domain"] for item in result["results"]} == {"traffic", "labor", "accounting"}
    assert set(calls) == {"traffic", "labor", "accounting"}
    assert result["status"] == "verified"
    assert len(result["citations"]) == 1


def test_ambiguous_query_needs_clarification(monkeypatch):
    monkeypatch.setattr(router, "get_settings", settings_without_llm)
    for name in ("run_traffic_agent", "run_labor_agent", "run_accounting_agent"):
        monkeypatch.setattr(router, name, lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not run")))
    result = router.run_router("Tôi muốn hỏi về quy định pháp luật", 5)
    assert result["status"] == "needs_clarification"
    assert result["results"] == []
    assert "lĩnh vực" in result["answer"]


def test_mocked_llm_classification_is_normalized(monkeypatch):
    settings = SimpleNamespace(openai_api_key="fake", openai_model="fake")
    monkeypatch.setattr(router, "_classify_with_llm", lambda query, settings: [
        {"domain": "labor", "query": "sub labor"},
        {"domain": "labor", "query": "duplicate"},
        {"domain": "illegal_domain", "query": "should drop"},
    ])
    result = router._classify_query("query", settings)
    assert result == [{"domain": "labor", "query": "sub labor"}]


def test_router_ask_endpoint(monkeypatch):
    expected = {
        "query": "Mức phạt giao thông?",
        "classifications": [{"domain": "traffic", "query": "Mức phạt giao thông?"}],
        "results": [{"domain": "traffic", "query": "Mức phạt giao thông?", "answer": "Theo evidence...", "status": "verified", "citations": [{"document_id": "traffic-1"}]}],
        "answer": "Theo evidence...",
        "citations": [{"document_id": "traffic-1"}],
        "status": "verified",
    }
    monkeypatch.setattr("app.main.run_router", lambda query, k: expected)
    response = TestClient(app).post("/router/ask", json={"query": "Mức phạt giao thông?", "k": 5})
    assert response.status_code == 200
    assert response.json() == expected


def test_expanded_query_is_sent_to_traffic_agent(monkeypatch):
    monkeypatch.setattr(router, "get_settings", settings_without_llm)
    captured = []

    def fake_traffic(query, k):
        captured.append(("traffic", query))
        return {"domain": "traffic", "answer": "ok", "status": "verified", "citations": []}

    monkeypatch.setattr(router, "run_traffic_agent", fake_traffic)
    result = router.run_router("muc phat nong do con", 5)
    assert result["classifications"][0]["domain"] == "traffic"
    assert "nồng độ cồn" in result["classifications"][0]["query"]
    assert captured[0][0] == "traffic"
    assert "nồng độ cồn" in captured[0][1]


def test_multi_vehicle_question_is_decomposed(monkeypatch):
    settings = settings_without_llm()
    monkeypatch.setattr(router, "get_settings", lambda: settings)
    captured = []

    def fake_traffic(query, k, sub_queries=None):
        captured.append(sub_queries or [])
        return {"query": query, "answer": "ok", "status": "verified", "citations": []}

    monkeypatch.setattr(router, "run_traffic_agent", fake_traffic)
    result = router.run_router(
        "Xe máy vượt đèn đỏ bị phạt bao nhiêu và ô tô vượt đèn đỏ bị phạt bao nhiêu?",
        5,
    )
    assert len(captured) == 1
    assert len(captured[0]) == 2
    assert "xe máy" in captured[0][0].casefold()
    assert "ô tô" in captured[0][1].casefold()


def test_contextual_followup_is_rewritten_for_retrieval():
    history = [
        {"role": "user", "content": "Hộ kinh doanh có phải xuất hóa đơn điện tử không?"},
        {"role": "assistant", "content": "Có căn cứ..."},
    ]
    rewritten = router._rewrite_followup_query("Cụ thể hơn?", history)
    assert rewritten.startswith("Hộ kinh doanh có phải xuất hóa đơn điện tử không?")
    assert rewritten.endswith("Cụ thể hơn?")


def test_explicit_new_query_is_not_rewritten():
    history = [{"role": "user", "content": "Người lao động nghỉ phép năm bao nhiêu ngày?"}]
    query = "Ô tô vượt đèn đỏ bị phạt bao nhiêu?"
    assert router._rewrite_followup_query(query, history) == query


def test_explicit_tax_enforcement_query_is_not_rewritten():
    history = [{"role": "user", "content": "Khi nào người nộp thuế được hoàn thuế giá trị gia tăng?"}]
    query = "Những trường hợp nào bị cưỡng chế thi hành quyết định hành chính về thuế?"
    assert router._rewrite_followup_query(query, history) == query
