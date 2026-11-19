from app.crawler import html_to_text, legal_records


def test_html_to_canonical_records_preserves_article_and_clause():
    html = """
    <html><script>ignore()</script><div id='divContent'>
      <h2>Chương II</h2><h3>Điều 8. Xử phạt</h3>
      <p>1. Phạt tiền từ 1 đến 2 đồng.</p>
      <p>2. Tước quyền sử dụng giấy phép.</p>
    </div></html>
    """
    records = legal_records(html_to_text(html), "file://traffic.html", "Luật giao thông", "168/2024/NĐ-CP")
    assert len(records) == 2
    assert records[0]["chuong"] == "Chương II"
    assert records[0]["dieu"] == "Điều 8"
    assert records[0]["khoan"] == "Khoản 1"
    assert records[0]["so_hieu"] == "168/2024/NĐ-CP"
    assert "script" not in records[0]["text"]


def test_unstructured_source_still_matches_schema():
    records = legal_records("Nội dung văn bản", "file://35-2024-qh15.pdf")
    assert records[0]["dieu"] == "Điều Toàn văn"
    assert set(("source", "so_hieu", "ten_van_ban", "chuong", "dieu", "tieu_de_dieu", "khoan", "text")) <= records[0].keys()
