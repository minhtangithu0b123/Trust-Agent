from types import SimpleNamespace

from fastapi.testclient import TestClient
from langchain_core.documents import Document

import app.agents.accounting_agent as accounting_agent
import app.agents.labor_agent as labor_agent
from app.main import app
from app.retrieval import HybridResult


class FakeModel:
    def __init__(self):
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        if self.calls == 1:
            return {"action": "search", "query": "domain query"}
        return {
            "action": "final",
            "answer": "Quy định pháp luật: theo evidence.",
            "cited_document_ids": ["domain-1"],
        }


def settings():
    return SimpleNamespace(openai_api_key=None, openai_model="test-model")


def fake_retriever_factory(captured, domain):
    class Retriever:
        def search(self, query, k):
            captured["query"] = query
            return [HybridResult(Document(page_content="evidence", metadata={"id": "domain-1", "domain": domain}), 0.1)]

    return lambda _settings, domain=None: Retriever()


def test_labor_search_expands_and_locks_domain(monkeypatch):
    captured = {}
    monkeypatch.setattr(labor_agent, "get_settings", settings)
    monkeypatch.setattr(labor_agent, "get_hybrid_retriever", fake_retriever_factory(captured, "labor"))
    results = labor_agent.search_labor_law("hop dong lao dong", 5)
    assert "hợp đồng lao động" in captured["query"]
    assert results[0]["metadata"]["domain"] == "labor"


def test_accounting_search_expands_and_locks_domain(monkeypatch):
    captured = {}
    monkeypatch.setattr(accounting_agent, "get_settings", settings)
    monkeypatch.setattr(accounting_agent, "get_hybrid_retriever", fake_retriever_factory(captured, "accounting"))
    results = accounting_agent.search_accounting_law("hoa don dien tu", 5)
    assert "hóa đơn điện tử" in captured["query"]
    assert results[0]["metadata"]["domain"] == "accounting"


def test_labor_and_accounting_agents_use_shared_react_loop(monkeypatch):
    labor_evidence = {"document_id": "domain-1", "text": "labor", "metadata": {"id": "domain-1", "domain": "labor"}, "citation": {"document_id": "domain-1"}}
    accounting_evidence = {"document_id": "domain-1", "text": "accounting", "metadata": {"id": "domain-1", "domain": "accounting"}, "citation": {"document_id": "domain-1"}}
    monkeypatch.setattr(labor_agent, "get_settings", settings)
    monkeypatch.setattr(accounting_agent, "get_settings", settings)
    monkeypatch.setattr(labor_agent, "search_labor_law", lambda query, k=5: [labor_evidence])
    monkeypatch.setattr(accounting_agent, "search_accounting_law", lambda query, k=5: [accounting_evidence])
    assert labor_agent.run_labor_agent("lương", model=FakeModel())["status"] == "verified"
    assert accounting_agent.run_accounting_agent("thuế", model=FakeModel())["status"] == "verified"


def test_labor_and_accounting_endpoints(monkeypatch):
    monkeypatch.setattr("app.main.run_labor_agent", lambda query, k: {"query": query, "answer": "labor", "status": "verified", "citations": []})
    monkeypatch.setattr("app.main.run_accounting_agent", lambda query, k: {"query": query, "answer": "accounting", "status": "verified", "citations": []})
    client = TestClient(app)
    labor_response = client.post("/agents/labor/ask", json={"query": "  lương  ", "k": 5})
    accounting_response = client.post("/agents/accounting/ask", json={"query": "  thuế  ", "k": 5})
    assert labor_response.status_code == 200
    assert accounting_response.status_code == 200
    assert labor_response.json()["answer"] == "labor"
    assert accounting_response.json()["answer"] == "accounting"
