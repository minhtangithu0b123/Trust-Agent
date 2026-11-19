from app.hop_planner import plan_next_hop


def test_accounting_hop_finds_missing_exception_and_effective_date():
    plan = plan_next_hop(
        "Hộ kinh doanh có phải lập hóa đơn điện tử không, ngoại lệ nào và hiệu lực từ khi nào?",
        "accounting",
        [{"text": "Hộ kinh doanh có trách nhiệm lập hóa đơn điện tử.", "metadata": {}}],
    )
    assert plan.hop == 2
    assert "exception" in plan.missing_facets
    assert "effective_date" in plan.missing_facets
    assert any("ngoại lệ" in query for query in plan.queries)


def test_simple_query_does_not_trigger_second_hop():
    plan = plan_next_hop("Mức phạt nồng độ cồn khi lái xe máy?", "traffic", [])
    assert plan.queries == ()


def test_traffic_points_hop_detects_missing_points_evidence():
    plan = plan_next_hop(
        "Ô tô vượt đèn đỏ bị phạt bao nhiêu và bị trừ bao nhiêu điểm?",
        "traffic",
        [{"text": "Phạt tiền từ 18.000.000 đồng đến 20.000.000 đồng.", "metadata": {}}],
    )
    assert "points" in plan.missing_facets
    assert any("trừ bao nhiêu điểm" in query for query in plan.queries)
