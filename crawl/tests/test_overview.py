from types import SimpleNamespace

from app.domains import DomainConfig
from app.overview import build_domain_overview, format_overview_answer


class FakeStore:
    def get(self, include=None):
        return {
            "metadatas": [
                {
                    "domain": "labor",
                    "so_hieu": "45/2019/QH14",
                    "ten_van_ban": "Bộ luật Lao động 2019",
                    "source": "test://labor",
                    "chuong": "Chương VII",
                    "dieu": "Điều 113",
                },
                {
                    "domain": "labor",
                    "so_hieu": "45/2019/QH14",
                    "ten_van_ban": "Bộ luật Lao động 2019",
                    "source": "test://labor",
                    "chuong": "Chương VII",
                    "dieu": "Điều 114",
                },
                {
                    "domain": "traffic",
                    "so_hieu": "traffic-doc",
                    "ten_van_ban": "Traffic",
                    "source": "test://traffic",
                    "chuong": "Chương I",
                    "dieu": "Điều 1",
                },
            ]
        }


def test_overview_groups_chapters_and_articles(monkeypatch):
    monkeypatch.setattr("app.overview.get_vectorstore", lambda settings, domain: FakeStore())
    config = DomainConfig("labor", "legal_labor", "data/raw/lao_dong.json", "labor", {})
    result = build_domain_overview(SimpleNamespace(), config)

    assert result["status"] == "overview"
    assert result["document_count"] == 2
    assert result["documents"][0]["chapters"][0]["article_count"] == 2
    assert "Chương VII" in format_overview_answer(result)
