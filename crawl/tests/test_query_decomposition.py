import pytest
from app import router

def test_query_decomposition_preserves_sub_queries():
    items = [
        {
            "domain": "traffic",
            "query": "Anh A vượt đèn đỏ không đội mũ bảo hiểm",
            "sub_queries": [
                "mức phạt vượt đèn đỏ xe máy",
                "mức phạt không đội mũ bảo hiểm",
                "mức phạt nồng độ cồn xe máy",
            ],
        }
    ]
    expanded = router._expand_classifications(items, "Anh A vi phạm giao thông")
    assert len(expanded) == 1
    assert "sub_queries" in expanded[0]
    assert len(expanded[0]["sub_queries"]) == 3
    assert "mức phạt vượt đèn đỏ xe máy" in expanded[0]["sub_queries"]
