from app.normalization import normalize_record, repair_text


def test_repair_mojibake():
    assert "Luật" in repair_text("LuÃƒÂ¢t")


def test_normalized_metadata():
    record_id, document = normalize_record({
        "source": "https://example.test/labor",
        "so_hieu": "45/2019/QH14",
        "ten_van_ban": "Luật Lao động 2019",
        "chuong": "Chương I",
        "dieu": "Điều 1",
        "tieu_de_dieu": "Phạm vi điều chỉnh",
        "khoan": "Khoản 1",
        "text": "Nội dung pháp luật lao động.",
    }, 0)
    assert len(record_id) == 24
    assert document.metadata["domain"] == "labor"
    assert document.metadata["status"] == "unknown"
    assert document.metadata["effective_from"] == ""
