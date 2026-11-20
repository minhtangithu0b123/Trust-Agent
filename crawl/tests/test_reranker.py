from types import SimpleNamespace

from langchain_core.documents import Document

from app.reranker import rerank
from app.retrieval import HybridResult


def test_reranker_is_disabled_by_default():
    results = [
        HybridResult(Document(page_content="a", metadata={"id": "a"}), 0.2),
        HybridResult(Document(page_content="b", metadata={"id": "b"}), 0.1),
    ]
    assert rerank("query", results, SimpleNamespace(reranker_enabled=False)) == results


def test_reranker_falls_back_when_model_fails(monkeypatch):
    results = [
        HybridResult(Document(page_content="a", metadata={"id": "a"}), 0.2),
        HybridResult(Document(page_content="b", metadata={"id": "b"}), 0.1),
    ]

    def fail(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr("app.reranker._load_cross_encoder", fail)
    assert [item.document.metadata["id"] for item in rerank(
        "query", results, SimpleNamespace(reranker_enabled=True)
    )] == ["a", "b"]


def test_reranker_can_promote_semantically_better_candidate(monkeypatch):
    results = [
        HybridResult(Document(page_content="broad traffic rule", metadata={"id": "a"}), 0.2),
        HybridResult(Document(page_content="alcohol concentration motorcycle penalty", metadata={"id": "b"}), 0.1),
    ]

    class FakeModel:
        def predict(self, pairs):
            return [0.1, 0.9]

    monkeypatch.setattr("app.reranker._load_cross_encoder", lambda *args: FakeModel())
    reranked = rerank("motorcycle alcohol penalty", results, SimpleNamespace(reranker_enabled=True))
    assert reranked[0].document.metadata["id"] == "b"
