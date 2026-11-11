from types import SimpleNamespace

from fastapi.testclient import TestClient
from langchain_core.documents import Document

import app.agents.traffic_agent as traffic_agent
from app.main import app
from app.retrieval import HybridResult


class FakeModel:
    def __init__(self, decisions):
        self.decisions = iter(decisions)

    def invoke(self, prompt):
        return next(self.decisions)


def evidence(document_id="traffic-1"):
    return {
        "document_id": document_id,
        "text": "Quy định về nồng độ cồn.",
        "metadata": {"id": document_id, "domain": "traffic", "dieu": "Điều 6", "khoan": "Khoản 1", "source": "test"},
        "citation": {"document_id": document_id, "dieu": "Điều 6", "khoan": "Khoản 1", "source": "test"},
    }


def test_traffic_agent_searches_then_returns_verified_citation(monkeypatch):
    observed = evidence()
    monkeypatch.setattr(traffic_agent, "search_traffic_law", lambda query, k=5: [observed])
    model = FakeModel([
        traffic_agent.ToolDecision(action="search", query="nồng độ cồn"),
        traffic_agent.ToolDecision(action="final", answer="Quy định pháp luật: theo evidence.", cited_document_ids=["traffic-1"]),
    ])
    result = traffic_agent.run_traffic_agent("Mức phạt nồng độ cồn?", model=model)
    assert result["status"] == "verified"
    assert result["citations"][0]["document_id"] == "traffic-1"


def test_traffic_agent_rejects_citation_not_observed(monkeypatch):
    monkeypatch.setattr(traffic_agent, "search_traffic_law", lambda query, k=5: [evidence()])
    model = FakeModel([
        traffic_agent.ToolDecision(action="search", query="nồng độ cồn"),
        traffic_agent.ToolDecision(action="final", answer="Kết luận", cited_document_ids=["not-observed"]),
    ])
    result = traffic_agent.run_traffic_agent("nồng độ cồn", model=model)
    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []


def test_traffic_agent_insufficient_phrase_is_safe(monkeypatch):
    monkeypatch.setattr(traffic_agent, "search_traffic_law", lambda query, k=5: [evidence()])
    model = FakeModel([
        traffic_agent.ToolDecision(action="search", query="nồng độ cồn"),
        traffic_agent.ToolDecision(
            action="final",
            answer="Chưa đủ căn cứ từ dữ liệu hiện có để kết luận.",
            cited_document_ids=["traffic-1"],
        ),
    ])
    result = traffic_agent.run_traffic_agent("nồng độ cồn", model=model)
    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []


def test_search_tool_is_locked_to_traffic(monkeypatch):
    captured = {}

    class Retriever:
        def search(self, query, k):
            return [HybridResult(Document(page_content="text", metadata={"id": "t1", "domain": "traffic"}), 0.1)]

    def fake_retriever(settings, domain):
        captured["domain"] = domain
        return Retriever()

    monkeypatch.setattr(traffic_agent, "get_hybrid_retriever", fake_retriever)
    result = traffic_agent.search_traffic_law("query")
    assert captured["domain"] == "traffic"
    assert result[0]["document_id"] == "t1"


def test_traffic_agent_endpoint(monkeypatch):
    expected = {"query": "Mức phạt?", "answer": "ok", "status": "verified", "citations": []}
    monkeypatch.setattr("app.main.run_traffic_agent", lambda query, k: expected)
    response = TestClient(app).post("/agents/traffic/ask", json={"query": "  Mức   phạt? ", "k": 5})
    assert response.status_code == 200
    assert response.json() == expected





def test_traffic_agent_uses_configured_openai_settings_without_exposing_key(monkeypatch):
    captured = {}
    decisions = iter([
        traffic_agent.ToolDecision(action="search", query="traffic query"),
        traffic_agent.ToolDecision(action="final", answer="Quy định pháp luật: theo evidence.", cited_document_ids=["traffic-1"]),
    ])

    class FakeChatOpenAI:
        def __init__(self, *, model, api_key, temperature):
            captured["model"] = model
            captured["key_configured"] = api_key == "test-secret-not-exposed"
            captured["temperature"] = temperature

        def with_structured_output(self, schema):
            return self

        def invoke(self, prompt):
            return next(decisions)

    monkeypatch.setattr(traffic_agent, "get_settings", lambda: SimpleNamespace(
        openai_api_key="test-secret-not-exposed",
        openai_model="configured-model",
    ))
    monkeypatch.setattr("langchain_openai.ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(traffic_agent, "search_traffic_law", lambda query, k=5: [evidence()])

    result = traffic_agent.run_traffic_agent("Mức phạt giao thông?")
    assert result["status"] == "verified"
    assert captured == {
        "model": "configured-model",
        "key_configured": True,
        "temperature": 0,
    }


def test_traffic_agent_hallucinated_article_downgraded_by_guardrail(monkeypatch):
    """Verifies that if traffic agent LLM produces a hallucinated article not in evidence,
    guardrail downgrades status to unverified with warnings."""
    monkeypatch.setattr(traffic_agent, "search_traffic_law", lambda query, k=5: [evidence("traffic-1")])
    # LLM cites valid doc_id "traffic-1" but hallucinates "Điều 999" in text
    model = FakeModel([
        traffic_agent.ToolDecision(action="search", query="nồng độ cồn"),
        traffic_agent.ToolDecision(
            action="final",
            answer="Căn cứ Điều 999 Nghị định 168/2024/NĐ-CP mức phạt là rất cao.",
            cited_document_ids=["traffic-1"],
        ),
    ])
    result = traffic_agent.run_traffic_agent("Mức phạt nồng độ cồn?", model=model)
    assert result["status"] == "unverified"
    assert result["citations"] == []
    assert len(result.get("guardrail_warnings", [])) >= 1
    assert "Điều 999" in result["guardrail_warnings"][0]
    assert "[CẢNH BÁO:" in result["answer"]


def test_traffic_agent_robust_with_evidence_lacking_citation_key(monkeypatch):
    """Verifies that evidence lacking explicit 'citation' key (e.g. raw dict) does not crash with KeyError."""
    raw_evidence = {
        "document_id": "traffic-raw-1",
        "text": "Xử phạt vi phạm giao thông.",
        "metadata": {
            "id": "traffic-raw-1",
            "domain": "traffic",
            "so_hieu": "168/2024/NĐ-CP",
            "dieu": "Điều 6",
            "khoan": "Khoản 1",
            "source": "test",
        },
        # note: no 'citation' key here
    }
    monkeypatch.setattr(traffic_agent, "search_traffic_law", lambda query, k=5: [raw_evidence])
    model = FakeModel([
        traffic_agent.ToolDecision(action="search", query="nồng độ cồn"),
        traffic_agent.ToolDecision(
            action="final",
            answer="Theo Điều 6 số 168/2024/NĐ-CP xử phạt vi phạm.",
            cited_document_ids=["traffic-raw-1"],
        ),
    ])
    result = traffic_agent.run_traffic_agent("Xử phạt nồng độ cồn?", model=model)
    assert result["status"] == "verified"
    assert len(result["citations"]) == 1
    assert result["citations"][0]["document_id"] == "traffic-raw-1"
    assert result["citations"][0]["dieu"] == "Điều 6"


def test_traffic_agent_with_evidence_primary_key_id(monkeypatch):
    """Verifies that evidence using 'id' (without 'document_id' at top level)
    is properly recognized by _finalize_node and not rejected as insufficient."""
    raw_evidence = {
        "id": "traffic-id-only-1",
        "text": "Xử phạt vi phạm giao thông theo Điều 6.",
        "metadata": {
            "id": "traffic-id-only-1",
            "domain": "traffic",
            "so_hieu": "168/2024/NĐ-CP",
            "dieu": "Điều 6",
            "khoan": "Khoản 1",
            "source": "test",
        },
    }
    monkeypatch.setattr(traffic_agent, "search_traffic_law", lambda query, k=5: [raw_evidence])
    model = FakeModel([
        traffic_agent.ToolDecision(action="search", query="nồng độ cồn"),
        traffic_agent.ToolDecision(
            action="final",
            answer="Theo Điều 6 số 168/2024/NĐ-CP xử phạt vi phạm.",
            cited_document_ids=["traffic-id-only-1"],
        ),
    ])
    result = traffic_agent.run_traffic_agent("Xử phạt nồng độ cồn?", model=model)
    assert result["status"] == "verified"
    assert len(result["citations"]) == 1
    assert result["citations"][0]["document_id"] == "traffic-id-only-1"
    assert result["citations"][0]["dieu"] == "Điều 6"





def test_ambiguous_helmet_query_requests_vehicle_type():
    result = traffic_agent.run_traffic_agent("khong doi mu bao hiem")
    assert result["status"] == "needs_clarification"
    assert result["citations"] == []
    assert "lo\u1ea1i ph\u01b0\u01a1ng ti\u1ec7n" in result["answer"]