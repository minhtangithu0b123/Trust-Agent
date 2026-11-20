from app.self_rag import critique_evidence


def test_self_rag_requests_missing_traffic_points():
    critique = critique_evidence(
        "Ô tô vượt đèn đỏ bị phạt bao nhiêu và bị trừ bao nhiêu điểm?",
        "traffic",
        [{
            "document_id": "penalty",
            "text": "Phạt tiền từ 18.000.000 đồng đến 20.000.000 đồng.",
            "metadata": {"domain": "traffic"},
        }],
        draft="Ô tô bị phạt từ 18 đến 20 triệu đồng.",
        cited_document_ids=["penalty"],
    )
    assert critique.should_retrieve is True
    assert critique.evidence_sufficient is False
    assert "points" in critique.missing_aspects
    assert critique.follow_up_queries


def test_self_rag_accepts_grounded_simple_evidence():
    critique = critique_evidence(
        "Mức phạt nồng độ cồn khi lái xe máy?",
        "traffic",
        [{
            "document_id": "alcohol",
            "text": "Phạt tiền theo quy định xử phạt nồng độ cồn.",
            "metadata": {"domain": "traffic"},
        }],
        draft="Theo evidence.",
        cited_document_ids=["alcohol"],
    )
    assert critique.should_retrieve is False
    assert critique.answer_supported is True
