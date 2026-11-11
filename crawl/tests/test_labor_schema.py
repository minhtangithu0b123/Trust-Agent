from pathlib import Path

from app.normalization import load_labor_documents


def test_real_labor_dataset_schema():
    path = Path(__file__).parents[1] / "data" / "raw" / "lao_dong.json"
    pairs = load_labor_documents(path)
    assert len(pairs) == 1110
    for record_id, document in pairs[:10]:
        assert record_id == document.metadata["id"]
        assert document.metadata["domain"] == "labor"
        assert document.page_content
    retirement_records = [
        document for _, document in pairs if document.metadata.get("so_hieu") == "135/2020/NĐ-CP"
    ]
    assert len(retirement_records) == 2
    assert any("năm 2026, nam 61 tuổi 6 tháng, nữ 57 tuổi" in doc.page_content for doc in retirement_records)
