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


def test_red_light_search_does_not_inject_motorcycle_fallback(monkeypatch):
    queries = []

    def fake_search(*args):
        queries.append(args[3])
        return [evidence("car-red-light")]

    monkeypatch.setattr(traffic_agent, "search_domain_law", fake_search)
    result = traffic_agent.search_traffic_law("Ô tô vượt đèn đỏ bị phạt bao nhiêu?")

    assert result[0]["document_id"] == "car-red-light"
    assert len(queries) == 1
    assert "xe mô tô" not in queries[0].lower()
    assert "điều 7" not in queries[0].lower()


def test_agent_search_preserves_original_vehicle_constraint(monkeypatch):
    searched = []

    def fake_search(query, k=5):
        searched.append(query)
        return [evidence("traffic-car")]

    monkeypatch.setattr(traffic_agent, "search_traffic_law", fake_search)
    model = FakeModel([
        traffic_agent.ToolDecision(
            action="search",
            query="không chấp hành hiệu lệnh đèn tín hiệu giao thông",
        ),
        traffic_agent.ToolDecision(
            action="final",
            answer="Quy định pháp luật: theo evidence.",
            cited_document_ids=["traffic-car"],
        ),
        traffic_agent.ToolDecision(
            action="final",
            answer="Quy định pháp luật: theo evidence.",
            cited_document_ids=["traffic-car"],
        ),
    ])

    traffic_agent.run_traffic_agent("Ô tô vượt đèn đỏ bị phạt bao nhiêu?", model=model)

    assert len(searched) == 2
    assert "Ô tô vượt đèn đỏ" in searched[0]
    assert "không chấp hành hiệu lệnh" in searched[0]


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
    assert result["answer"].startswith("Chưa đủ căn cứ")


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


def test_red_light_answer_rejects_alcohol_points_branch(monkeypatch):
    monkeypatch.setattr(
        traffic_agent,
        "run_domain_agent",
        lambda *args, **kwargs: {
            "query": "Ô tô vượt đèn đỏ có bị trừ điểm không?",
            "answer": "Ô tô bị trừ 10 điểm giấy phép lái xe.",
            "status": "verified",
            "citations": [{"document_id": "traffic-1"}],
        },
    )
    result = traffic_agent.run_traffic_agent("Ô tô vượt đèn đỏ có bị trừ điểm không?")
    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []
    assert "Chưa đủ căn cứ" in result["answer"]


def test_motorbike_high_alcohol_answer_rejects_car_fine(monkeypatch):
    """The 18--20 million bracket must not be shown for a motorcycle query."""
    monkeypatch.setattr(
        traffic_agent,
        "run_domain_agent",
        lambda *args, **kwargs: {
            "query": "Xe máy có nồng độ cồn vượt quá 0,4 mg/lít khí thở bị phạt thế nào?",
            "answer": "Phạt từ 18.000.000 đến 20.000.000 đồng theo Điều 8 Khoản 9.",
            "status": "verified",
            "citations": [{"document_id": "traffic-car-alcohol"}],
        },
    )

    result = traffic_agent.run_traffic_agent(
        "Xe máy có nồng độ cồn vượt quá 0,4 mg/lít khí thở bị phạt thế nào?"
    )

    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []


def test_helmet_answer_cannot_invent_article_12(monkeypatch):
    monkeypatch.setattr(
        traffic_agent,
        "run_domain_agent",
        lambda *args, **kwargs: {
            "query": "Người điều khiển xe máy không đội mũ bảo hiểm bị phạt bao nhiêu?",
            "answer": "Phạt từ 400.000 đến 600.000 đồng theo Điều 12 Khoản 5 và Điều 7 Khoản 2.",
            "status": "verified",
            "citations": [{"document_id": "traffic-helmet"}],
        },
    )
    result = traffic_agent.run_traffic_agent("Người điều khiển xe máy không đội mũ bảo hiểm bị phạt bao nhiêu?")
    assert result["status"] == "insufficient_evidence"
    assert "Điều 12" not in result["answer"]





def test_driver_helmet_answer_keeps_article_7_and_drops_passenger_article_12(monkeypatch):
    monkeypatch.setattr(
        traffic_agent,
        "run_domain_agent",
        lambda *args, **kwargs: {
            "query": "Ng\u01b0\u1eddi \u0111i\u1ec1u khi\u1ec3n xe m\u00e1y kh\u00f4ng \u0111\u1ed9i m\u0169 b\u1ea3o hi\u1ec3m",
            "answer": "Ph\u1ea1t t\u1eeb 400.000 \u0111\u1ebfn 600.000 \u0111\u1ed3ng theo \u0110i\u1ec1u 12 Kho\u1ea3n 5 v\u00e0 \u0110i\u1ec1u 7 Kho\u1ea3n 2.",
            "status": "verified",
            "citations": [
                {"document_id": "traffic-passenger", "dieu": "\u0110i\u1ec1u 12", "khoan": "Kho\u1ea3n 5"},
                {"document_id": "traffic-driver", "dieu": "\u0110i\u1ec1u 7", "khoan": "Kho\u1ea3n 2"},
            ],
        },
    )
    result = traffic_agent.run_traffic_agent("Ng\u01b0\u1eddi \u0111i\u1ec1u khi\u1ec3n xe m\u00e1y kh\u00f4ng \u0111\u1ed9i m\u0169 b\u1ea3o hi\u1ec3m")
    assert result["status"] == "verified"
    assert "\u0110i\u1ec1u 12" not in result["answer"]
    assert "\u0110i\u1ec1u 7" in result["answer"]
    assert [item["document_id"] for item in result["citations"]] == ["traffic-driver"]


def test_ambiguous_helmet_query_requests_vehicle_type():
    result = traffic_agent.run_traffic_agent("khong doi mu bao hiem")
    assert result["status"] == "needs_clarification"
    assert result["citations"] == []
    assert "lo\u1ea1i ph\u01b0\u01a1ng ti\u1ec7n" in result["answer"]
