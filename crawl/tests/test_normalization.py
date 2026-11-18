from pathlib import Path

from app.domains import DomainConfig
from app.normalization import load_documents, normalize_record, repair_text


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


def test_accounting_article_six_title_is_rejoined():
    _, document = normalize_record({
        "source": "test://accounting",
        "so_hieu": "88/2015/QH13",
        "ten_van_ban": "Luật Kế toán 2015",
        "chuong": "Chương I",
        "dieu": "Điều 6",
        "tieu_de_dieu": "Nguyên",
        "khoan": "Khoản 1",
        "text": "tắc kế toán: giá trị tài sản được ghi nhận theo giá gốc.",
    }, 0, domain="accounting")
    assert document.metadata["tieu_de_dieu"] == "Nguyên tắc kế toán"
    assert document.page_content.startswith("Nguyên tắc kế toán.")


def test_load_documents_deduplicates_same_legal_structure(tmp_path: Path):
    import json

    records = [
        {
            "source": "data",
            "so_hieu": "168/2024/NĐ-CP",
            "ten_van_ban": "Nghị định",
            "chuong": "Chương II",
            "dieu": "Điều 7",
            "tieu_de_dieu": "Xử phạt",
            "khoan": "Khoản 7",
            "text": "[Nghị định - Điều 7 - Khoản 7] Nguồn: data Nội dung: nội dung sạch.",
        },
        {
            "source": "data",
            "so_hieu": "168/2024/NĐ-CP",
            "ten_van_ban": "Nghị định",
            "chuong": "Chương II",
            "dieu": "Điều 7",
            "tieu_de_dieu": "Xử phạt",
            "khoan": "Khoản 7",
            "text": "Nội dung sạch.",
        },
    ]
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    config = DomainConfig("traffic", "legal_traffic", str(path), "traffic", {})
    pairs = load_documents(path, config)
    assert len(pairs) == 1
    assert pairs[0][1].page_content == "Nội dung sạch."
