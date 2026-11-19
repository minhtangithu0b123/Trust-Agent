from app.clarification import clarification_for_query


def test_traffic_asks_for_vehicle_when_speed_is_missing_vehicle():
    assert clarification_for_query("Chạy quá tốc độ bị phạt thế nào?", "traffic")


def test_traffic_asks_driver_or_passenger_for_seat_belt():
    answer = clarification_for_query("Không thắt dây an toàn bị phạt thế nào?", "traffic")
    assert answer and "người lái" in answer and "người được chở" in answer


def test_traffic_does_not_ask_when_vehicle_is_explicit():
    assert clarification_for_query("Ô tô không thắt dây an toàn bị phạt thế nào?", "traffic") is None


def test_labor_asks_which_party_for_termination_notice():
    assert clarification_for_query("Đơn phương chấm dứt hợp đồng phải báo trước bao lâu?", "labor")


def test_accounting_asks_for_taxpayer_type():
    assert clarification_for_query("Phải nộp những loại thuế nào?", "accounting")


def test_clear_labor_question_is_not_blocked():
    assert clarification_for_query("Người lao động ký hợp đồng thử việc tối đa bao nhiêu ngày?", "labor") is None
