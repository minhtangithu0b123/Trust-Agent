from app.clarification import (
    build_clarification_decision,
    fill_query_slots,
)
from app.router import preflight_query


def test_slot_filling_extracts_explicit_vehicle_and_topic():
    slots = fill_query_slots("Xe máy chạy quá tốc độ bị phạt thế nào?", "traffic")
    assert slots.vehicle == "motorbike"
    assert slots.topic == "speed"


def test_hybrid_clarification_requests_missing_vehicle_before_retrieval():
    decision = build_clarification_decision("Chạy quá tốc độ bị phạt thế nào?", "traffic")
    assert decision.action == "clarify"
    assert decision.missing_slots == ("vehicle",)
    assert decision.question
    assert decision.source == "rules"


def test_hybrid_clarification_proceeds_when_required_slot_is_present():
    decision = build_clarification_decision("Ô tô chạy quá tốc độ bị phạt thế nào?", "traffic")
    assert decision.action == "proceed"
    assert decision.slots.vehicle == "car"
    assert decision.question is None


def test_paid_preflight_blocks_payment_for_clarification_turn():
    result = preflight_query("Chạy quá tốc độ bị phạt thế nào?")
    assert result is not None
    assert result["status"] == "needs_clarification"
    assert result["answer"]


def test_paid_preflight_allows_payment_after_required_slot_is_present():
    assert preflight_query("Ô tô chạy quá tốc độ bị phạt thế nào?") is None
