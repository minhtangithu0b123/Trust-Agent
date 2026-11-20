from app.self_query import build_query_plan


def test_car_speed_query_uses_article_six_clause_five():
    plan = build_query_plan("O to chay qua toc do 15 km h bi phat the nao?", "traffic")
    assert plan.metadata_filter["dieu"] == "\u0110i\u1ec1u 6"
    assert plan.metadata_filter["khoan"] == "Kho\u1ea3n 5"


def test_motorbike_highway_query_uses_article_seven_clause_seven():
    plan = build_query_plan("Xe may di vao duong cao toc bi phat the nao?", "traffic")
    assert plan.metadata_filter["dieu"] == "\u0110i\u1ec1u 7"
    assert plan.metadata_filter["khoan"] == "Kho\u1ea3n 7"


def test_trial_pay_query_includes_article_twenty_six():
    plan = build_query_plan("Nguoi lao dong thu viec huong it nhat 85 phan tram luong?", "labor")
    assert "\u0110i\u1ec1u 26" in plan.metadata_filter["dieu"]


def test_parent_child_house_gift_uses_pit_exemption_article():
    plan = build_query_plan("Cha me tang nha cho con co phai nop thue thu nhap ca nhan khong?", "accounting")
    assert plan.metadata_filter["dieu"] == "\u0110i\u1ec1u 4"
    assert plan.metadata_filter["khoan"] == "Kho\u1ea3n 1"
