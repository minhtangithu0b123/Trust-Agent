from types import SimpleNamespace

from langchain_core.documents import Document

from app.answering import (
    GenerationResult,
    INSUFFICIENT_EVIDENCE,
    answer_question,
    verify_citations,
)
from app.retrieval import HybridResult


class MockProvider:
    def __init__(self, cited_ids):
        self.cited_ids = cited_ids

    def generate(self, query, context):
        return GenerationResult("Câu trả lời dựa trên evidence.", self.cited_ids)


def evidence():
    return [HybridResult(Document(
        page_content="Người lao động có quyền nghỉ hằng năm theo quy định.",
        metadata={
            "id": "doc-1", "domain": "labor", "so_hieu": "45/2019/QH14",
            "ten_van_ban": "Bộ luật Lao động 2019", "chuong": "Chương VII",
            "dieu": "Điều 113", "khoan": "Khoản 1", "source": "test://labor",
            "status": "unknown", "effective_from": "",
        },
    ), 0.03)]


def fake_retriever(items):
    return SimpleNamespace(search=lambda query, k: items)


def test_valid_citation_id_is_verified(monkeypatch):
    items = evidence()
    monkeypatch.setattr("app.answering.get_hybrid_retriever", lambda settings, domain: fake_retriever(items))
    result = answer_question("Quyền nghỉ phép?", 5, SimpleNamespace(labor_domain="labor"), MockProvider(["doc-1"]))
    assert result["status"] == "verified"
    assert result["citations"][0]["document_id"] == "doc-1"
    assert result["citations"][0]["dieu"] == "Điều 113"


def test_invalid_citation_id_is_rejected(monkeypatch):
    items = evidence()
    monkeypatch.setattr("app.answering.get_hybrid_retriever", lambda settings, domain: fake_retriever(items))
    result = answer_question("Quyền nghỉ phép?", 5, SimpleNamespace(labor_domain="labor"), MockProvider(["not-in-evidence"]))
    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []
    assert result["answer"] == INSUFFICIENT_EVIDENCE


def test_no_evidence_returns_insufficient(monkeypatch):
    monkeypatch.setattr("app.answering.get_hybrid_retriever", lambda settings, domain: fake_retriever([]))
    result = answer_question("Câu hỏi không có dữ liệu", 5, SimpleNamespace(labor_domain="labor"), MockProvider(["doc-1"]))
    assert result["status"] == "insufficient_evidence"
    assert result["answer"] == INSUFFICIENT_EVIDENCE


def test_missing_api_key_is_safe(monkeypatch):
    items = evidence()
    monkeypatch.setattr("app.answering.get_hybrid_retriever", lambda settings, domain: fake_retriever(items))
    settings = SimpleNamespace(labor_domain="labor", openai_api_key=None, openai_model="gpt-4o-mini")
    result = answer_question("Quyền nghỉ phép?", 5, settings)
    assert result["status"] == "provider_error"
    assert result["citations"] == []


def test_verify_citations_rejects_unknown_id_directly():
    result = verify_citations(GenerationResult("answer", ["unknown"]), evidence())
    assert result[0] == "insufficient_evidence"

def test_ask_endpoint_does_not_crash_without_api_key(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    items = evidence()
    monkeypatch.setattr("app.answering.get_hybrid_retriever", lambda settings, domain: fake_retriever(items))
    monkeypatch.setattr("app.main.get_settings", lambda: SimpleNamespace(
        labor_domain="labor", openai_api_key=None, openai_model="gpt-4o-mini"
    ))
    response = TestClient(app).post("/ask", json={"query": "Quyền nghỉ phép?", "k": 5})
    assert response.status_code == 200
    assert response.json()["status"] == "provider_error"
class InsufficientProvider:
    def generate(self, query, context):
        return GenerationResult(
            "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận.", ["doc-1"]
        )


def test_insufficient_evidence_answer_is_not_verified(monkeypatch):
    items = evidence()
    monkeypatch.setattr("app.answering.get_hybrid_retriever", lambda settings, domain: fake_retriever(items))
    result = answer_question(
        "Quyền nghỉ phép?", 5, SimpleNamespace(labor_domain="labor"), InsufficientProvider()
    )
    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []
