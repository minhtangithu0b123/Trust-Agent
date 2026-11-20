from app.agents.labor_agent import _reject_unsupported_multiple_contract_claim
from app.agents.traffic_agent import _reject_mixed_alcohol_thresholds
from app.clarification import clarification_for_query
from app.router import _keyword_classify
from app.query_normalization import expand_query_for_retrieval
from app.self_query import build_query_plan


def test_keyword_fallback_covers_implicit_labor_and_tax_questions():
    assert {item["domain"] for item in _keyword_classify(
        "cong ty yeu cau nhan vien lam them 4 tieng moi ngay"
    )} == {"labor"}
    assert {item["domain"] for item in _keyword_classify(
        "cong ty co quyen giu bang tot nghiep ban goc"
    )} == {"labor"}
    assert {item["domain"] for item in _keyword_classify(
        "cha me khong co thu nhap dang ky nguoi phu thuoc giam tru gia canh"
    )} == {"accounting"}
    assert {item["domain"] for item in _keyword_classify(
        "nhan vien chinh thuc va freelancer phai dong thue va bao hiem xa hoi"
    )} == {"labor", "accounting"}


def test_keyword_fallback_covers_cases_26_to_35():
    cases = [
        ("dieu khien xe may bang mot tay su dung dien thoai", {"traffic"}),
        ("nguoi lao dong tu choi lam them gio", {"labor"}),
        ("tien thuong tet luong thang 13 chiu thue thu nhap ca nhan", {"accounting"}),
        ("cho ban muon xe bi phat nguoi ai nop phat", {"traffic"}),
        ("cong ty dieu chuyen nhan vien giam luong", {"labor"}),
        ("ca nhan cho thue nha phai ke khai nop thue", {"accounting"}),
        ("giay phep lai xe bi tru het diem", {"traffic"}),
        ("hop dong dao tao nghi viec hoan tra chi phi dao tao", {"labor"}),
        ("doanh nghiep thua lo chuyen lo giam thue", {"accounting"}),
        (
            "nhan vien giao hang tai nan cong ty boi thuong chi phi duoc tru thue doanh nghiep",
            {"traffic", "labor", "accounting"},
        ),
    ]
    for query, expected in cases:
        assert {item["domain"] for item in _keyword_classify(query)} == expected


def test_keyword_fallback_covers_cases_56_to_65_without_vehicle_tax_false_positives():
    cases = [
        ("xe may leo len via he tranh un tac", {"traffic"}),
        ("nguoi lao dong lam viec vao ngay le tet", {"labor"}),
        ("doanh nghiep cham nop thue trong 30 ngay tien cham nop", {"accounting"}),
        ("nguoi ngoi sau xe may khong doi mu bao hiem", {"traffic"}),
        ("nguoi lao dong nghi thai san hop dong het han", {"labor"}),
        ("ca nhan ban o to da qua su dung co phai dong thue", {"accounting"}),
        ("cho nguoi khong co giay phep lai xe muon o to", {"traffic"}),
        ("cong ty yeu cau nhan vien dat coc truoc khi ky hop dong", {"labor"}),
        ("doanh nghiep mua o to khau tru toan bo thue gia tri gia tang", {"accounting"}),
        ("cong ty thue nguoi lao dong nuoc ngoai hop dong bao hiem xa hoi thue", {"labor", "accounting"}),
    ]
    for query, expected in cases:
        assert {item["domain"] for item in _keyword_classify(query)} == expected


def test_keyword_fallback_covers_cases_66_to_75():
    cases = [
        ("xe may di vao duong cao toc", {"traffic"}),
        ("nguoi lao dong trinh do dai hoc thoi gian thu viec toi da", {"labor"}),
        ("phu cap an trua xang xe nhan vien chiu thue thu nhap ca nhan", {"accounting"}),
        ("o to dung do truoc cong benh vien", {"traffic"}),
        ("nguoi lao dong nghi viec vi da ket hon", {"labor"}),
        ("ho kinh doanh nhieu cua hang cac tinh ke khai nop thue", {"accounting"}),
        ("o to gay tai nan roi roi khoi hien truong", {"traffic"}),
        ("cong ty pha san no 3 thang tien luong", {"labor"}),
        ("hoa don sai thue suat thue gia tri gia tang", {"accounting"}),
        ("cong ty tra luong nhan vien bang co phieu nghia vu thue", {"labor", "accounting"}),
    ]
    for query, expected in cases:
        assert {item["domain"] for item in _keyword_classify(query)} == expected


def test_multi_topic_traffic_plan_keeps_all_offences():
    plan = build_query_plan(
        "xe may nong do con khong doi mu bao hiem khong co bang lai",
        "traffic",
    )
    assert set(plan.metadata_filter["traffic_topics"]) == {"helmet", "alcohol"}


def test_new_tax_and_labor_retrieval_expansions_are_canonical():
    tax_query = expand_query_for_retrieval(
        "tien trung thuong xo so 2 ty dong",
        "tien trung thuong xo so 2 ty dong",
        "accounting",
    )
    labor_query = expand_query_for_retrieval(
        "hop dong lao dong het han van tiep tuc lam viec",
        "hop dong lao dong het han van tiep tuc lam viec",
        "labor",
    )
    assert "trúng thưởng xổ số" in tax_query
    assert "vượt trên 20 triệu đồng" in tax_query
    assert "trong 30 ngày kể từ ngày hết hạn" in labor_query


def test_unused_leave_after_resignation_keeps_annual_leave_plan():
    plan = build_query_plan(
        "nghi viec thanh toan ngay phep nam chua su dung",
        "labor",
    )
    assert plan.metadata_filter["dieu"] == "Điều 113"


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
