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

    def fake_answer(query, k, settings, domain=None):
        calls.append(domain)
        return {
            "domain": domain,
            "answer": f"Answer for {domain}",
            "status": "verified",
            "citations": [{"document_id": "shared-doc", "dieu": "Điều 1"}],
        }

    monkeypatch.setattr(router, "answer_question", fake_answer)
    result = router.run_router("quy định về giao thông, lao động và thuế", 5)
    assert {item["domain"] for item in result["classifications"]} == {
        "traffic", "labor", "accounting"
    }
    assert {item["domain"] for item in result["results"]} == {
        "traffic", "labor", "accounting"
    }
    assert set(calls) == {"traffic", "labor", "accounting"}
    assert result["status"] == "verified"
    assert len(result["citations"]) == 1


def test_ambiguous_query_needs_clarification(monkeypatch):
    monkeypatch.setattr(router, "get_settings", settings_without_llm)
    monkeypatch.setattr(router, "answer_question", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not run")))
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
        "results": [{
            "domain": "traffic",
            "query": "Mức phạt giao thông?",
            "answer": "Theo evidence...",
            "status": "verified",
            "citations": [{"document_id": "traffic-1"}],
        }],
        "answer": "Theo evidence...",
        "citations": [{"document_id": "traffic-1"}],
        "status": "verified",
    }
    monkeypatch.setattr("app.main.run_router", lambda query, k: expected)
    response = TestClient(app).post("/router/ask", json={"query": "Mức phạt giao thông?", "k": 5})
    assert response.status_code == 200
    assert response.json() == expected

def test_expanded_query_is_sent_to_traffic_branch(monkeypatch):
    monkeypatch.setattr(router, "get_settings", settings_without_llm)
    captured = []

    def fake_answer(query, k, settings, domain=None):
        captured.append((domain, query))
        return {"domain": domain, "answer": "ok", "status": "verified", "citations": []}

    monkeypatch.setattr(router, "answer_question", fake_answer)
    result = router.run_router("muc phat nong do con", 5)
    assert result["classifications"][0]["domain"] == "traffic"
    assert "nồng độ cồn" in result["classifications"][0]["query"]
    assert captured[0][0] == "traffic"
    assert "nồng độ cồn" in captured[0][1]
