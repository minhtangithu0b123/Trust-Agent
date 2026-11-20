from app.agents.labor_agent import _reject_unsupported_multiple_contract_claim
from app.agents.traffic_agent import _reject_mixed_alcohol_thresholds
from app.clarification import clarification_for_query
from app.query_normalization import expand_query_for_retrieval
from app.self_query import build_query_plan


def test_labor_resignation_query_expands_and_targets_termination_articles():
    query = "Người lao động nghỉ việc có cần báo trước không?"
    routing = "nguoi lao dong nghi viec co can bao truoc khong"
    expanded = expand_query_for_retrieval(query, routing, "labor")
    plan = build_query_plan(query, "labor")
    assert "thời hạn báo trước" in expanded
    assert plan.metadata_filter["dieu"] == ["Điều 35", "Điều 36", "Điều 37"]


def test_accounting_revenue_query_expands_threshold_terms():
    expanded = expand_query_for_retrieval(
        "Hộ kinh doanh có doanh thu 800 triệu đồng/năm phải đóng thuế gì?",
        "ho kinh doanh co doanh thu 800 trieu dong nam phai dong thue gi",
        "accounting",
    )
    assert "800.000.000 đồng" in expanded
    assert "ngưỡng doanh thu" in expanded


def test_freelancer_query_expands_both_income_tax_categories():
    expanded = expand_query_for_retrieval(
        "Làm nhân viên và freelancer thì đóng thuế thế nào?",
        "lam nhan vien va freelancer thi dong thue the nao",
        "accounting",
    )
    assert "thu nhập từ tiền lương, tiền công" in expanded
    assert "thu nhập từ kinh doanh" in expanded


def test_alcohol_guardrail_rejects_mixed_brackets():
    result = _reject_mixed_alcohol_thresholds(
        "Xe máy có nồng độ cồn vượt quá 0,4 mg/lít khí thở bị phạt thế nào?",
        {
            "status": "verified",
            "answer": "Phạt từ 18.000.000 đến 20.000.000 đồng và từ 6.000.000 đến 8.000.000 đồng.",
            "citations": [{"document_id": "traffic-1"}],
        },
    )
    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []


def test_multiple_contract_guardrail_rejects_all_employers_claim():
    result = _reject_unsupported_multiple_contract_claim(
        "Một người lao động ký hợp đồng với hai công ty cùng lúc đóng BHXH thế nào?",
        {
            "status": "verified",
            "answer": "Mỗi công ty đều đóng bảo hiểm xã hội cho người lao động.",
            "citations": [{"document_id": "labor-1"}],
        },
    )
    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []


def test_multiple_contract_plan_keeps_article_168():
    plan = build_query_plan(
        "Một người lao động ký hợp đồng với hai công ty cùng lúc phải đóng bảo hiểm thế nào?",
        "labor",
    )
    assert "Điều 168" in plan.metadata_filter["dieu"]


def test_missing_vehicle_questions_ask_for_required_context():
    assert clarification_for_query("Tôi không mang bằng lái xe thì bị phạt bao nhiêu?", "traffic")
    assert clarification_for_query("Sáng hôm sau còn nồng độ cồn thì bị phạt không?", "traffic")
