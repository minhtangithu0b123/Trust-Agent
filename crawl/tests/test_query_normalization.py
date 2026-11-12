from types import SimpleNamespace

from app.query_normalization import clean_query, normalize_for_routing
from app.router import _classify_query


def _settings():
    return SimpleNamespace(openai_api_key=None)


def test_normalize_for_routing_removes_vietnamese_accents():
    assert normalize_for_routing("Mức phạt nồng độ cồn") == "muc phat nong do con"


def test_clean_query_preserves_legal_reference():
    query = "  Nghị định 168/2024/NĐ-CP\n Điều 6, Khoản 11; 36/2024/QH15  "
    assert clean_query(query) == "Nghị định 168/2024/NĐ-CP Điều 6, Khoản 11; 36/2024/QH15"


def test_clean_query_collapses_whitespace_only():
    assert clean_query("  Điều   6\n\tKhoản  11  ") == "Điều 6 Khoản 11"


def test_accented_and_unaccented_traffic_route_same():
    assert _classify_query("Mức phạt nồng độ cồn?", _settings())[0]["domain"] == "traffic"
    assert _classify_query("muc phat nong do con?", _settings())[0]["domain"] == "traffic"


def test_accented_and_unaccented_labor_route_same():
    assert _classify_query("Người lao động nghỉ phép?", _settings())[0]["domain"] == "labor"
    assert _classify_query("nguoi lao dong nghi phep?", _settings())[0]["domain"] == "labor"


def test_accented_and_unaccented_accounting_route_same():
    assert _classify_query("Hóa đơn và thuế?", _settings())[0]["domain"] == "accounting"
    assert _classify_query("hoa don va thue?", _settings())[0]["domain"] == "accounting"

from app.query_normalization import expand_query_for_retrieval


def test_unaccented_traffic_query_expands_to_canonical_terms():
    expanded = expand_query_for_retrieval(
        "muc phat nong do con", "muc phat nong do con", "traffic"
    )
    assert "nồng độ cồn" in expanded
    assert "xử phạt vi phạm nồng độ cồn" in expanded


def test_unmatched_query_is_unchanged_by_expansion():
    query = "cau hoi khong co khai niem da biet"
    assert expand_query_for_retrieval(query, query, "traffic") == query


def test_expansion_preserves_legal_identifier():
    query = "muc phat nong do con theo Nghị định 168/2024/NĐ-CP"
    expanded = expand_query_for_retrieval(query, "muc phat nong do con theo nghi dinh 168/2024/nd-cp", "traffic")
    assert "168/2024/NĐ-CP" in expanded


def test_labor_rights_query_expands_to_canonical_terms():
    expanded = expand_query_for_retrieval(
        "ng\u01b0\u1eddi lao \u0111\u1ed9ng c\u00f3 nh\u1eefng quy\u1ec1n l\u1ee3i g\u00ec",
        "nguoi lao dong co nhung quyen loi gi",
        "labor",
    )
    assert "quy\u1ec1n l\u1ee3i ng\u01b0\u1eddi lao \u0111\u1ed9ng" in expanded


def test_annual_leave_query_expands_to_article_113_terms():
    expanded = expand_query_for_retrieval(
        "Người lao động được nghỉ hằng năm bao nhiêu ngày?",
        "nguoi lao dong duoc nghi hang nam bao nhieu ngay",
        "labor",
    )
    assert "Điều 113 Bộ luật Lao động" in expanded
    assert "số ngày nghỉ hằng năm" in expanded


def test_employee_termination_query_expands_to_article_35_terms():
    expanded = expand_query_for_retrieval(
        "Khi nào người lao động được đơn phương chấm dứt hợp đồng lao động?",
        "khi nao nguoi lao dong duoc don phuong cham dut hop dong lao dong",
        "labor",
    )
    assert "Điều 35" in expanded
    assert "thời hạn báo trước" in expanded

def test_accounting_query_expands_to_canonical_terms():
    expanded = expand_query_for_retrieval(
        "Lu\u1eadt K\u1ebf to\u00e1n quy \u0111\u1ecbnh nh\u1eefng nguy\u00ean t\u1eafc k\u1ebf to\u00e1n n\u00e0o",
        "luat ke toan quy dinh nhung nguyen tac ke toan nao",
        "accounting",
    )
    assert "nguy\u00ean t\u1eafc k\u1ebf to\u00e1n" in expanded
    assert "Lu\u1eadt K\u1ebf to\u00e1n 2015 Điều 6" in expanded
