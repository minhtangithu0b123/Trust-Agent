"""Unit tests for Router and LLM Synthesizer (crawl/app/router.py).

Tests:
1. Multi-domain query fan-out and synthesis using mocked OpenAI gpt-4o-mini.
2. Synthesizer prompt construction (_build_synthesizer_user_prompt).
3. Citation Guardrail verification of synthesized output (pass vs hallucinated downgrade).
4. Fallback synthesis when OpenAI API key is absent or LLM fails.
5. Insufficient evidence handling when branch agents have no evidence.
6. Single domain bypasses multi-agent synthesis and preserves original branch answer.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import app.router as router
from app.citation_guardrail import INSUFFICIENT_EVIDENCE


def mock_traffic_branch():
    return {
        "domain": "traffic",
        "query": "Lái xe gây tai nạn giao thông",
        "answer": "Theo Điều 6 Nghị định 168/2024/NĐ-CP, người điều khiển xe gây tai nạn bị xử phạt.",
        "status": "verified",
        "citations": [
            {
                "document_id": "traffic-doc-1",
                "so_hieu": "168/2024/NĐ-CP",
                "dieu": "Điều 6",
                "ten_van_ban": "Nghị định 168/2024/NĐ-CP",
            }
        ],
    }


def mock_labor_branch():
    return {
        "domain": "labor",
        "query": "Trách nhiệm bồi thường của người lao động",
        "answer": "Theo Điều 113 Bộ luật Lao động 45/2019/QH14, người lao động có quyền và trách nhiệm theo hợp đồng.",
        "status": "verified",
        "citations": [
            {
                "document_id": "labor-doc-1",
                "so_hieu": "45/2019/QH14",
                "dieu": "Điều 113",
                "ten_van_ban": "Bộ luật Lao động 2019",
            }
        ],
    }


class TestPromptConstruction:
    def test_build_synthesizer_user_prompt_includes_all_domains(self):
        results = [mock_traffic_branch(), mock_labor_branch()]
        query = "Lái xe công ty gây tai nạn thì xử lý ra sao?"

        prompt = router._build_synthesizer_user_prompt(query, results)

        assert query in prompt
        assert "LĨNH VỰC: GIAO THÔNG" in prompt
        assert "LĨNH VỰC: LAO ĐỘNG" in prompt
        assert "168/2024/NĐ-CP" in prompt
        assert "45/2019/QH14" in prompt
        assert "traffic-doc-1" in prompt
        assert "labor-doc-1" in prompt


class TestLLMSynthesizerExecution:
    def test_synthesizer_with_mocked_gpt_4o_mini(self, monkeypatch):
        """Verifies multi-domain synthesizer invokes gpt-4o-mini structured output."""
        synthesized_text = (
            "Tổng hợp pháp lý:\n"
            "1. Về giao thông: Căn cứ Điều 6 Nghị định 168/2024/NĐ-CP, lái xe chịu xử phạt.\n"
            "2. Về lao động: Theo Điều 113 Bộ luật Lao động 45/2019/QH14, thực hiện quyền theo hợp đồng."
        )

        class MockStructuredOutputModel:
            def invoke(self, messages):
                return router.SynthesizerPayload(
                    answer=synthesized_text,
                    cited_document_ids=["traffic-doc-1", "labor-doc-1"],
                )

        class MockChatOpenAI:
            def __init__(self, model, api_key, temperature):
                assert model == "gpt-4o-mini"
                assert api_key == "mock-openai-key"

            def with_structured_output(self, schema):
                return MockStructuredOutputModel()

        monkeypatch.setattr("langchain_openai.ChatOpenAI", MockChatOpenAI)

        settings = SimpleNamespace(
            openai_api_key="mock-openai-key",
            openai_model="gpt-4o-mini",
            labor_domain="labor",
        )
        monkeypatch.setattr(router, "get_settings", lambda: settings)

        verified_results = [mock_traffic_branch(), mock_labor_branch()]
        synthesized = router._synthesize_with_llm(
            query="Tài xế công ty gây tai nạn?",
            verified_results=verified_results,
            settings=settings,
        )

        assert synthesized == synthesized_text

    def test_synthesizer_hallucination_is_caught_by_guardrail(self, monkeypatch):
        """If LLM synthesizer invents a legal article not in evidence, guardrail downgrades to unverified."""
        # Synthesizer hallucinating "Điều 999" and "Điều 777"
        hallucinated_text = (
            "Tổng hợp:\n"
            "Theo Điều 999 Nghị định 168/2024/NĐ-CP và Điều 777 Bộ luật Lao động 45/2019/QH14, "
            "doanh nghiệp phải chịu trách nhiệm toàn bộ."
        )

        class MockStructuredOutputModel:
            def invoke(self, messages):
                return router.SynthesizerPayload(
                    answer=hallucinated_text,
                    cited_document_ids=["traffic-doc-1", "labor-doc-1"],
                )

        class MockChatOpenAI:
            def __init__(self, *args, **kwargs):
                pass

            def with_structured_output(self, schema):
                return MockStructuredOutputModel()

        monkeypatch.setattr("langchain_openai.ChatOpenAI", MockChatOpenAI)
        settings = SimpleNamespace(
            openai_api_key="mock-key",
            openai_model="gpt-4o-mini",
            labor_domain="labor",
        )
        monkeypatch.setattr(router, "get_settings", lambda: settings)

        state: router.RouterState = {
            "query": "Tài xế công ty gây tai nạn?",
            "results": [mock_traffic_branch(), mock_labor_branch()],
        }

        output = router.synthesize_results(state)

        # Status must be downgraded to unverified due to hallucinated articles
        assert output["status"] == "unverified"
        assert output["guardrail_status"] == "unverified"
        assert len(output["guardrail_warnings"]) >= 1
        assert "Điều 999" in output["guardrail_warnings"][0] or "Điều 777" in output["guardrail_warnings"][0]
        assert "[CẢNH BÁO:" in output["final_answer"]
        assert output["final_citations"] == []

    def test_fallback_synthesizer_when_no_api_key(self, monkeypatch):
        settings = SimpleNamespace(openai_api_key=None, labor_domain="labor")
        monkeypatch.setattr(router, "get_settings", lambda: settings)

        state: router.RouterState = {
            "query": "Lái xe gây tai nạn và trách nhiệm lao động?",
            "results": [mock_traffic_branch(), mock_labor_branch()],
        }

        output = router.synthesize_results(state)

        assert output["status"] == "verified"
        assert "### Lĩnh vực Giao thông" in output["final_answer"]
        assert "### Lĩnh vực Lao động" in output["final_answer"]
        assert len(output["final_citations"]) == 2

    def test_insufficient_evidence_when_branches_fail(self):
        state: router.RouterState = {
            "query": "Chủ đề không có dữ liệu pháp lý",
            "results": [
                {"domain": "traffic", "answer": INSUFFICIENT_EVIDENCE, "status": "insufficient_evidence"},
                {"domain": "labor", "answer": INSUFFICIENT_EVIDENCE, "status": "insufficient_evidence"},
            ],
        }

        output = router.synthesize_results(state)

        assert output["status"] == "insufficient_evidence"
        assert output["final_answer"] == INSUFFICIENT_EVIDENCE
        assert output["final_citations"] == []

    def test_single_branch_bypasses_synthesis(self):
        traffic_only = mock_traffic_branch()
        state: router.RouterState = {
            "query": "Chỉ hỏi về mức phạt nồng độ cồn",
            "results": [traffic_only],
        }

        output = router.synthesize_results(state)

        assert output["status"] == "verified"
        assert output["final_answer"] == traffic_only["answer"]
        assert len(output["final_citations"]) == 1
        assert output["final_citations"][0]["document_id"] == "traffic-doc-1"


class TestRouterEndToEndSynthesizer:
    def test_full_router_multi_domain_synthesis(self, monkeypatch):
        class MockClassifierModel:
            def invoke(self, prompt):
                return router.ClassificationPayload(
                    classifications=[
                        router.Classification(domain="traffic", query="vi phạm giao thông"),
                        router.Classification(domain="labor", query="hợp đồng lao động"),
                    ]
                )

        class MockSynthesizerModel:
            def invoke(self, messages):
                return router.SynthesizerPayload(
                    answer=(
                        "Kết luận:\n"
                        "Theo Điều 6 Nghị định 168/2024/NĐ-CP, tài xế chịu phạt vi phạm giao thông. "
                        "Theo Điều 113 Bộ luật Lao động 45/2019/QH14, xem xét theo chế độ hợp đồng lao động."
                    ),
                    cited_document_ids=["traffic-doc-1", "labor-doc-1"],
                )

        class MockChatOpenAI:
            def __init__(self, *args, **kwargs):
                pass

            def with_structured_output(self, schema):
                if schema is router.ClassificationPayload:
                    return MockClassifierModel()
                return MockSynthesizerModel()

        monkeypatch.setattr("langchain_openai.ChatOpenAI", MockChatOpenAI)
        monkeypatch.setattr(router, "run_traffic_agent", lambda q, k: mock_traffic_branch())
        monkeypatch.setattr(router, "run_labor_agent", lambda q, k: mock_labor_branch())

        settings = SimpleNamespace(
            openai_api_key="mock-key",
            openai_model="gpt-4o-mini",
            labor_domain="labor",
        )
        monkeypatch.setattr(router, "get_settings", lambda: settings)

        result = router.run_router(
            query="Tài xế công ty uống rượu bia gây tai nạn và sa thải theo luật lao động?",
            k=5,
        )

        assert result["status"] == "verified"
        assert len(result["classifications"]) == 2
        assert len(result["results"]) == 2
        assert "Nghị định 168/2024/NĐ-CP" in result["answer"]
        assert "Bộ luật Lao động 45/2019/QH14" in result["answer"]
        assert len(result["citations"]) == 2
