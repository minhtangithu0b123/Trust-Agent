import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace
from app.intent_guardrail import get_intent_guardrail
import app.main as main
from app.main import SearchRequest, app
from app.router import run_router


def test_intent_guardrail_greetings():
    guardrail = get_intent_guardrail()
    greetings = [
        "chào bạn",
        "xin chào bot nhé",
        "hello",
        "hi bot",
        "cảm ơn bạn nhiều",
        "tạm biệt nhé",
        "bạn là ai",
    ]
    for q in greetings:
        res = guardrail.check_intent(q)
        assert res.intent == "greeting", f"Failed for {q}"
        assert res.response is not None


def test_intent_guardrail_out_of_scope():
    guardrail = get_intent_guardrail()
    out_of_scope_queries = [
        "thời tiết hôm nay thế nào",
        "dự báo thời tiết Hà Nội",
        "hôm nay ăn gì ngon",
        "công thức nấu ăn món phở bò",
        "viết cho tôi bài thơ tình lãng mạn",
        "kết quả bóng đá ngoại hạng anh",
        "kể một chuyện cười đi",
        "hướng dẫn lập trình python",
    ]
    for q in out_of_scope_queries:
        res = guardrail.check_intent(q)
        assert res.intent == "out_of_scope", f"Failed for {q}"
        assert res.response is not None


def test_intent_guardrail_in_scope():
    guardrail = get_intent_guardrail()
    legal_queries = [
        "vượt đèn đỏ xe máy phạt bao nhiêu",
        "nồng độ cồn ô tô bị giữ bằng bao lâu",
        "mức lương thử việc theo luật lao động",
        "người sử dụng lao động đơn phương chấm dứt hợp đồng",
        "thuế giá trị gia tăng được khấu trừ khi nào",
        "hóa đơn điện tử có sai sót thì xử lý thế nào",
    ]
    for q in legal_queries:
        res = guardrail.check_intent(q)
        assert res.intent == "in_scope", f"Failed for {q}"
        assert res.response is None


def test_intent_guardrail_accepts_unaccented_legal_question():
    result = get_intent_guardrail().check_intent("muc phat nong do con xe may")
    assert result.intent == "in_scope"


def test_intent_guardrail_stops_unrecognized_input():
    for query in ("dskfjgsfkdg", "qwe zxc 123", "asdfghjkl"):
        res = get_intent_guardrail().check_intent(query)
        assert res.intent == "needs_clarification"
        assert res.response is not None


def test_router_stops_greetings_zero_api():
    result = run_router("chào bạn")
    assert result["status"] == "greeting"
    assert "Xin chào bạn" in result["answer"]
    assert result["citations"] == []
    assert result["classifications"] == []


def test_router_stops_out_of_scope_zero_api():
    result = run_router("thời tiết hôm nay thế nào")
    assert result["status"] == "out_of_scope"
    assert "nằm ngoài phạm vi tư vấn pháp lý" in result["answer"]
    assert result["citations"] == []
    assert result["classifications"] == []


def test_router_stops_short_social_messages_zero_api():
    for query in ("ok", "OK", "được rồi", "cam on ban", "bạn khỏe không"):
        result = run_router(query)
        assert result["status"] == "greeting"
        assert result["citations"] == []
        assert result["classifications"] == []
        assert "sẵn sàng" in result["answer"]


def test_router_stops_unrecognized_input_zero_api():
    result = run_router("dskfjgsfkdg")
    assert result["status"] == "needs_clarification"
    assert result["guardrail_status"] == "needs_clarification"
    assert result["citations"] == []
    assert result["classifications"] == []


def test_paid_validation_stops_unrecognized_input_zero_api():
    response = TestClient(app).post(
        "/paid/traffic/validate",
        json={"query": "dskfjgsfkdg", "k": 5},
    )
    assert response.status_code == 200
    assert response.json()["allowed"] is False
    assert response.json()["status"] == "needs_clarification"


@pytest.mark.parametrize("domain, query", [
    ("labor", "Người lao động thử việc được trả lương thế nào?"),
    ("accounting", "Tiền lãi gửi tiết kiệm có phải nộp thuế thu nhập cá nhân không?"),
])
def test_paid_ask_uses_the_same_router_as_the_free_ask(monkeypatch, domain, query):
    expected = {
        "query": query,
        "answer": "Câu trả lời có căn cứ.",
        "status": "verified",
        "citations": [{"document_id": f"{domain}-1"}],
        "classifications": [{"domain": domain, "query": query}],
    }
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(x402_enabled=True, x402_network="eip155:43113", index_version="test-index"),
    )
    router_calls = []
    stored_messages = []
    monkeypatch.setattr(
        main,
        "run_router",
        lambda actual_query, k, thread_id=None: router_calls.append((actual_query, k, thread_id)) or expected,
    )
    monkeypatch.setattr(main, "ensure_conversation", lambda conversation_id, default_title: {"id": conversation_id or "paid-conversation"})
    monkeypatch.setattr(main, "add_message", lambda *args, **kwargs: stored_messages.append((args, kwargs)))
    monkeypatch.setattr(
        main,
        "create_receipt",
        lambda answer, citations, index_version: {"receipt_id": "receipt-1", "leaf_hash": "hash-1", "index_version": index_version},
    )

    response = main.paid_router_ask(SearchRequest(query=query, k=5, conversation_id="paid-conversation"))

    assert response["answer"] == expected["answer"]
    assert response["classifications"] == expected["classifications"]
    assert response["payment"] == {"scheme": "x402", "network": "eip155:43113"}
    assert response["conversation_id"] == "paid-conversation"
    assert router_calls == [(query, 5, "paid-conversation")]
    assert [args[1] for args, _ in stored_messages] == ["user", "assistant"]
