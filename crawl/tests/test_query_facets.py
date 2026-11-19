from app.query_facets import extract_query_facets, facet_score


def test_vehicle_facet_promotes_matching_vehicle_and_penalizes_conflict():
    query = "Mức phạt nồng độ cồn khi lái xe máy"
    facets = extract_query_facets(query, "traffic")
    assert "motorbike" in facets.required_phrases
    assert facet_score(query, "người điều khiển xe mô tô có nồng độ cồn", "traffic") > 0
    assert facet_score(query, "người điều khiển ô tô có nồng độ cồn", "traffic") < 0


def test_facets_are_shared_across_domains():
    assert "hop dong lao dong" in extract_query_facets(
        "Hợp đồng lao động cần nội dung gì?", "labor"
    ).topic_phrases
    assert "ca nhan kinh doanh" in extract_query_facets(
        "Cá nhân kinh doanh phải nộp những loại thuế nào?", "accounting"
    ).topic_phrases
    assert "thu viec" in extract_query_facets(
        "Thời gian thử việc tối đa bao nhiêu ngày?", "labor"
    ).topic_phrases


def test_unrecognized_query_has_no_ranking_adjustment():
    assert facet_score("Xin chào", "một văn bản pháp luật", "labor") == 0.0
