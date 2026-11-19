from pathlib import Path

from app.normalization import load_labor_documents


def test_real_labor_dataset_schema():
    path = Path(__file__).parents[1] / "data" / "raw" / "lao_dong.json"
    pairs = load_labor_documents(path)
    # The corpus is extensible; keep the schema check without freezing the
    # test to the original MVP count.
    assert len(pairs) >= 1108
    for record_id, document in pairs[:10]:
        assert record_id == document.metadata["id"]
        assert document.metadata["domain"] == "labor"
        assert document.page_content


def test_normalized_records_expose_structured_retrieval_metadata():
    path = Path(__file__).parents[1] / "data" / "raw" / "lao_dong.json"
    _, document = load_labor_documents(path)[0]
    assert document.metadata["article_number"]
    assert document.metadata["clause_number"] or document.metadata["khoan"] == "Khoản Toàn văn"
    assert document.metadata["structure_key"]
    assert document.metadata["document_type"] in {"law", "decree", "circular", "other"}
