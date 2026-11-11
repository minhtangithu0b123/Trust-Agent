import pytest
from app.intent_guardrail import get_intent_guardrail
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
