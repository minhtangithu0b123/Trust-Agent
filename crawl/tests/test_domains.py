from langchain_core.documents import Document

from app.config import Settings
from app.domains import DOMAIN_CONFIGS
from app.normalization import load_documents
from app.retrieval import HybridRetriever


def test_domain_configs_have_separate_collections_and_existing_corpora():
    settings = Settings()
    assert set(DOMAIN_CONFIGS) == {"labor", "accounting", "traffic"}
    collections = {settings.domain_config(name).collection_name for name in DOMAIN_CONFIGS}
    assert collections == {"legal_labor", "legal_accounting", "legal_traffic"}
    for name, config in DOMAIN_CONFIGS.items():
        assert settings.resolve_path(config.data_path).exists(), name


def test_normalization_sets_domain_without_mixing():
    settings = Settings()
    labor_config = settings.domain_config("labor")
    traffic_config = settings.domain_config("traffic")
    labor_record = load_documents(settings.resolve_path(labor_config.data_path), labor_config)[0][1]
    traffic_record = load_documents(settings.resolve_path(traffic_config.data_path), traffic_config)[0][1]
    assert labor_record.metadata["domain"] == "labor"
    assert traffic_record.metadata["domain"] == "traffic"
    assert labor_record.metadata["domain"] != traffic_record.metadata["domain"]


def test_hybrid_refresh_and_dense_search_filter_domain(monkeypatch):
    settings = Settings()
    traffic_doc = Document(page_content="traffic evidence", metadata={"id": "traffic-1", "domain": "traffic"})
    labor_doc = Document(page_content="labor evidence", metadata={"id": "labor-1", "domain": "labor"})

    class Collection:
        def count(self):
            return 2

    class Store:
        _collection = Collection()

        def get(self, include):
            return {
                "ids": ["traffic-1", "labor-1"],
                "documents": ["traffic evidence", "labor evidence"],
                "metadatas": [traffic_doc.metadata, labor_doc.metadata],
            }

        def similarity_search(self, query, k, filter):
            assert filter == {"domain": "traffic"}
            return [traffic_doc]

    monkeypatch.setattr("app.retrieval.get_vectorstore", lambda settings, domain: Store())
    retriever = HybridRetriever(settings, domain="traffic")
    result = retriever.search("traffic", k=1)
    assert result[0].document.metadata["domain"] == "traffic"
    assert all(document.metadata["domain"] == "traffic" for document in retriever._documents.values())
def test_overview_domain_detection():
    from app.overview import detect_overview_domain

    assert detect_overview_domain("Luật lao động có gì?") == "labor"
    assert detect_overview_domain("Luật giao thông gồm những gì?") == "traffic"
    assert detect_overview_domain("Luật kế toán có nội dung gì?") == "accounting"
    assert detect_overview_domain("Mức phạt nồng độ cồn khi lái xe máy?") is None
    assert detect_overview_domain("Hợp đồng lao động cần có những nội dung gì?") is None
    assert detect_overview_domain("Hóa đơn điện tử cần có những nội dung gì?") is None


def test_tax_alias_keeps_accounting_canonical_config():
    from app.domains import get_domain_config

    assert get_domain_config("tax").name == "accounting"
    assert get_domain_config("thue").collection_name == "legal_accounting"
