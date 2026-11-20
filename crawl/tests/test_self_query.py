from app.query_normalization import expand_query_for_retrieval, normalize_for_routing
from app.self_query import build_query_plan


def test_traffic_car_query_is_locked_to_car_article():
    plan = build_query_plan("Ô tô vượt đèn đỏ bị phạt bao nhiêu?", "traffic")
    assert plan.metadata_filter["domain"] == "traffic"
    assert plan.metadata_filter["dieu"] == "Điều 6"
    assert plan.metadata_filter["khoan"] == "Khoản 9"


def test_traffic_expansion_does_not_introduce_a_conflicting_vehicle():
    query = "Ô tô vượt đèn đỏ bị phạt bao nhiêu?"
    expanded = expand_query_for_retrieval(query, normalize_for_routing(query), "traffic")
    plan = build_query_plan(expanded, "traffic")
    assert plan.metadata_filter["dieu"] == "Điều 6"


def test_traffic_motorbike_query_is_locked_to_motorbike_article():
    plan = build_query_plan("Xe máy vượt đèn đỏ bị phạt bao nhiêu?", "traffic")
    assert plan.metadata_filter["dieu"] == "Điều 7"
    assert plan.metadata_filter["khoan"] == "Khoản 7"


def test_real_unicode_motorbike_query_uses_article_seven_and_clause_seven():
    plan = build_query_plan("Xe m\u00e1y v\u01b0\u1ee3t \u0111\u00e8n \u0111\u1ecf b\u1ecb ph\u1ea1t bao nhi\u00eau?", "traffic")
    assert plan.metadata_filter["dieu"] == "\u0110i\u1ec1u 7"
    assert plan.metadata_filter["khoan"] == "Kho\u1ea3n 7"


def test_real_unicode_car_query_uses_article_six_and_clause_nine():
    plan = build_query_plan("\u00d4 t\u00f4 v\u01b0\u1ee3t \u0111\u00e8n \u0111\u1ecf b\u1ecb ph\u1ea1t bao nhi\u00eau?", "traffic")
    assert plan.metadata_filter["dieu"] == "\u0110i\u1ec1u 6"
    assert plan.metadata_filter["khoan"] == "Kho\u1ea3n 9"


def test_traffic_query_for_multiple_vehicle_types_is_not_overfiltered():
    plan = build_query_plan("Ô tô và xe máy vượt đèn đỏ bị phạt thế nào?", "traffic")
    assert "dieu" not in plan.metadata_filter


def test_specialized_vehicle_does_not_match_generic_motorbike():
    plan = build_query_plan("Xe may chuyen dung vuot qua toc do bi phat the nao?", "traffic")
    assert plan.metadata_filter["dieu"] == "\u0110i\u1ec1u 8"


def test_explicit_article_remains_authoritative():
    plan = build_query_plan("Ô tô, Điều 7 khoản 7 quy định gì?", "traffic")
    assert plan.metadata_filter["dieu"] == "Điều 7"
    assert plan.metadata_filter["khoan"] == "Khoản 7"


def test_labor_annual_leave_query_uses_leave_articles():
    plan = build_query_plan("Người lao động được nghỉ phép năm bao nhiêu ngày?", "labor")
    assert plan.metadata_filter["dieu"] == "Điều 113"
    assert plan.metadata_filter["khoan"] == ["Khoản 1", "Khoản 2"]
