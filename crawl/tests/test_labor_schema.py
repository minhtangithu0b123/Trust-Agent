from pathlib import Path

from app.normalization import load_labor_documents


def test_real_labor_dataset_schema():
    path = Path(__file__).parents[1] / "data" / "raw" / "lao_dong.json"
    pairs = load_labor_documents(path)
    assert len(pairs) == 1108
    for record_id, document in pairs[:10]:
        assert record_id == document.metadata["id"]
        assert document.metadata["domain"] == "labor"
        assert document.page_content
