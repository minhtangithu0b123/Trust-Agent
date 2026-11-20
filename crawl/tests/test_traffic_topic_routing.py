from app.self_query import build_query_plan
from app.normalization import normalize_record


def test_traffic_topics_are_planned_without_llm():
    passenger = build_query_plan(
        "Xe máy chở 2 người bị phạt bao nhiêu tiền?", "traffic"
    )
    assert passenger.metadata_filter["dieu"] == "Điều 7"
    assert passenger.metadata_filter["traffic_topics"] == "passenger_overload"

    phone = build_query_plan(
        "Người điều khiển xe máy dùng điện thoại khi lái xe bị phạt thế nào?",
        "traffic",
    )
    assert phone.metadata_filter["traffic_topics"] == "phone_use"


def test_traffic_clause_metadata_classifies_related_offences():
    record = {
        "source": "test://traffic",
        "so_hieu": "168/2024/NĐ-CP",
        "ten_van_ban": "Nghị định 168/2024/NĐ-CP",
        "chuong": "Chương II",
        "dieu": "Điều 7",
        "tieu_de_dieu": "Xử phạt người điều khiển xe mô tô",
        "khoan": "Khoản 2",
        "text": "Phạt tiền từ 400.000 đồng đến 600.000 đồng đối với hành vi chở theo 02 người trên xe; không đội mũ bảo hiểm hoặc đội mũ không cài quai đúng quy cách.",
    }
    _, document = normalize_record(record, 0, domain="traffic")
    assert set(document.metadata["traffic_topics"].split("|")) == {
        "passenger_overload",
        "helmet",
    }

