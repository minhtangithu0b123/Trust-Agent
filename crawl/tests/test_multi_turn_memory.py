"""Unit tests for LangGraph MemorySaver multi-turn context retention.

Tests:
1. Multi-turn conversation maintains and accumulates message history across turns for the same thread_id.
2. Separate thread_id/session_id instances are isolated from each other.
3. Message history is passed into query classification to resolve context-dependent follow-up questions.
4. /router/ask endpoint accepts and preserves thread_id and session_id across turns.
5. Independent custom MemorySaver checkpointers isolate test environments cleanly.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

import app.router as router
from app.main import app


def fake_traffic_agent(query, k):
    return {
        "domain": "traffic",
        "query": query,
        "answer": "Theo Nghị định 168/2024/NĐ-CP, mức phạt vi phạm nồng độ cồn là 6 đến 8 triệu đồng.",
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


def fake_labor_agent(query, k):
    return {
        "domain": "labor",
        "query": query,
        "answer": "Theo Điều 113 Bộ luật Lao động 45/2019/QH14, người lao động được nghỉ 12 ngày phép.",
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


class TestMemorySaverMultiTurn:
    def test_multi_turn_accumulates_history_with_same_thread_id(self, monkeypatch):
        checkpointer = MemorySaver()
        graph = router.build_router_graph(checkpointer=checkpointer)

        monkeypatch.setattr(router, "build_router_graph", lambda checkpointer=None: graph)
        monkeypatch.setattr(router, "run_traffic_agent", fake_traffic_agent)
        monkeypatch.setattr(router, "get_settings", lambda: SimpleNamespace(openai_api_key=None, labor_domain="labor"))

        thread_id = "test-thread-turn-123"

        # Turn 1: Traffic query
        res1 = router.run_router("Mức phạt nồng độ cồn xe máy?", k=5, thread_id=thread_id)
        assert res1["thread_id"] == thread_id
        assert res1["status"] == "verified"
        assert len(res1["results"]) == 1

        # Check state checkpoint after Turn 1
        state_t1 = graph.get_state({"configurable": {"thread_id": thread_id}})
        messages_t1 = state_t1.values.get("messages", [])
        assert len(messages_t1) == 2
        assert messages_t1[0]["role"] == "user"
        assert "nồng độ cồn" in messages_t1[0]["content"]
        assert messages_t1[1]["role"] == "assistant"

        # Turn 2: Follow-up query on same thread_id
        res2 = router.run_router("Thời hạn xử phạt giao thông là bao lâu?", k=5, thread_id=thread_id)
        assert res2["thread_id"] == thread_id
        assert res2["status"] == "verified"

        # Check state checkpoint after Turn 2: history must contain 4 messages (2 turns)
        state_t2 = graph.get_state({"configurable": {"thread_id": thread_id}})
        messages_t2 = state_t2.values.get("messages", [])
        assert len(messages_t2) == 4
        assert messages_t2[0]["content"] == messages_t1[0]["content"]
        assert messages_t2[2]["role"] == "user"
        assert "Thời hạn xử phạt" in messages_t2[2]["content"]
        assert messages_t2[3]["role"] == "assistant"

    def test_separate_thread_ids_have_isolated_memory(self, monkeypatch):
        checkpointer = MemorySaver()
        graph = router.build_router_graph(checkpointer=checkpointer)

        monkeypatch.setattr(router, "build_router_graph", lambda checkpointer=None: graph)
        monkeypatch.setattr(router, "run_traffic_agent", fake_traffic_agent)
        monkeypatch.setattr(router, "run_labor_agent", fake_labor_agent)
        monkeypatch.setattr(router, "get_settings", lambda: SimpleNamespace(openai_api_key=None, labor_domain="labor"))

        # User A interacts with traffic domain
        router.run_router("Mức phạt nồng độ cồn xe máy?", k=5, thread_id="thread-user-A")
        # User B interacts with labor domain
        router.run_router("Quy định nghỉ phép năm của người lao động?", k=5, thread_id="thread-user-B")

        state_a = graph.get_state({"configurable": {"thread_id": "thread-user-A"}})
        state_b = graph.get_state({"configurable": {"thread_id": "thread-user-B"}})

        messages_a = state_a.values.get("messages", [])
        messages_b = state_b.values.get("messages", [])

        # User A has only 2 messages about traffic
        assert len(messages_a) == 2
        assert "nồng độ cồn" in messages_a[0]["content"]

        # User B has only 2 messages about labor
        assert len(messages_b) == 2
        assert "nghỉ phép" in messages_b[0]["content"]

        # No memory bleed between sessions
        assert "nghỉ phép" not in messages_a[0]["content"]
        assert "nồng độ cồn" not in messages_b[0]["content"]

    def test_conversation_history_passed_to_llm_classifier(self, monkeypatch):
        """Verifies that previous messages in state are forwarded to LLM classifier prompt."""
        captured_prompts = []

        class MockStructuredOutputModel:
            def invoke(self, prompt):
                captured_prompts.append(prompt)
                return router.ClassificationPayload(
                    classifications=[router.Classification(domain="traffic", query="Tước bằng lái xe")]
                )

        class MockChatOpenAI:
            def __init__(self, *args, **kwargs):
                pass

            def with_structured_output(self, schema):
                return MockStructuredOutputModel()

        monkeypatch.setattr("langchain_openai.ChatOpenAI", MockChatOpenAI)
        settings = SimpleNamespace(openai_api_key="mock-key", openai_model="gpt-4o-mini")

        history = [
            {"role": "user", "content": "Nồng độ cồn vượt mức kịch khung bị phạt sao?"},
            {"role": "assistant", "content": "Bị phạt 6-8 triệu đồng theo Điều 6."},
        ]

        classifications = router._classify_with_llm(
            query="Có bị tước bằng lái không?",
            settings=settings,
            messages=history,
        )

        assert len(classifications) == 1
        assert classifications[0]["domain"] == "traffic"
        assert len(captured_prompts) == 1
        # Verify history was embedded into classification prompt
        assert "Lịch sử hội thoại:" in captured_prompts[0]
        assert "Nồng độ cồn vượt mức kịch khung" in captured_prompts[0]
        assert "Có bị tước bằng lái không?" in captured_prompts[0]

    def test_long_conversation_history_sliding_window_and_accumulation(self, monkeypatch):
        """Verifies that conversation history accumulates over 20+ turns without corruption,
        and that LLM classification prompt receives only a safe sliding window of recent messages
        to avoid token overflow."""
        captured_prompts = []

        class MockStructuredOutputModel:
            def invoke(self, prompt):
                captured_prompts.append(prompt)
                return router.ClassificationPayload(
                    classifications=[router.Classification(domain="traffic", query="câu hỏi turn 26")]
                )

        class MockChatOpenAI:
            def __init__(self, *args, **kwargs):
                pass

            def with_structured_output(self, schema):
                return MockStructuredOutputModel()

        monkeypatch.setattr("langchain_openai.ChatOpenAI", MockChatOpenAI)
        settings = SimpleNamespace(openai_api_key="mock-key", openai_model="gpt-4o-mini")

        # Simulate 25 turns (50 messages)
        long_history = []
        for i in range(1, 26):
            long_history.append({"role": "user", "content": f"Câu hỏi lượt {i} về luật"})
            long_history.append({"role": "assistant", "content": f"Câu trả lời lượt {i} chi tiết"})

        assert len(long_history) == 50

        classifications = router._classify_with_llm(
            query="Câu hỏi lượt 26 tiếp nối?",
            settings=settings,
            messages=long_history,
        )

        assert len(classifications) == 1
        assert len(captured_prompts) == 1
        prompt = captured_prompts[0]
        # Sliding window takes only recent 4 messages (turns 24 and 25)
        assert "Câu hỏi lượt 24" in prompt or "Câu hỏi lượt 25" in prompt
        # Very old turns (turn 1 to turn 20) must be truncated to prevent token window overflow
        assert "Câu hỏi lượt 1 " not in prompt
        assert "Câu hỏi lượt 5 " not in prompt
        assert "Câu hỏi lượt 10 " not in prompt


class TestRouterAskEndpointMultiTurn:
    def test_router_ask_endpoint_thread_id_retention(self, monkeypatch):
        checkpointer = MemorySaver()
        graph = router.build_router_graph(checkpointer=checkpointer)

        monkeypatch.setattr(router, "build_router_graph", lambda checkpointer=None: graph)
        monkeypatch.setattr(router, "run_traffic_agent", fake_traffic_agent)
        monkeypatch.setattr(router, "get_settings", lambda: SimpleNamespace(openai_api_key=None, labor_domain="labor"))

        client = TestClient(app)
        thread_id = "api-session-789"

        # Turn 1
        r1 = client.post("/router/ask", json={"query": "Mức phạt nồng độ cồn?", "k": 5, "thread_id": thread_id})
        assert r1.status_code == 200
        data1 = r1.json()
        assert data1["thread_id"] == thread_id
        assert data1["status"] == "verified"

        # Turn 2 with session_id (alias for thread_id)
        r2 = client.post("/router/ask", json={"query": "Tốc độ tối đa trong đô thị là bao nhiêu?", "k": 5, "session_id": thread_id})
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["thread_id"] == thread_id
        assert data2["session_id"] == thread_id

        # Verify history accumulated in checkpointer
        state = graph.get_state({"configurable": {"thread_id": thread_id}})
        assert len(state.values.get("messages", [])) == 4

    def test_multi_turn_clarification_then_resolution(self, monkeypatch):
        """Verifies that an ambiguous query triggers clarification and records messages,
        then a clarifying follow-up on the same thread_id resolves to an agent and retains full history."""
        checkpointer = MemorySaver()
        graph = router.build_router_graph(checkpointer=checkpointer)

        monkeypatch.setattr(router, "build_router_graph", lambda checkpointer=None: graph)
        monkeypatch.setattr(router, "run_traffic_agent", fake_traffic_agent)
        monkeypatch.setattr(router, "get_settings", lambda: SimpleNamespace(openai_api_key=None, labor_domain="labor"))

        thread_id = "test-clarify-thread"

        # Turn 1: Ambiguous greeting/query -> needs clarification
        res1 = router.run_router("Xin chào bạn, tôi muốn hỏi thủ tục", thread_id=thread_id)
        assert res1["status"] == "needs_clarification"
        assert res1["guardrail_status"] == "needs_clarification"
        assert router.CLARIFICATION_ANSWER in res1["answer"]

        # Checkpoint state has 2 messages (Turn 1)
        state1 = graph.get_state({"configurable": {"thread_id": thread_id}})
        assert len(state1.values.get("messages", [])) == 2
        assert state1.values["messages"][0]["role"] == "user"
        assert state1.values["messages"][1]["role"] == "assistant"

        # Turn 2: Clarifying query on the same thread_id
        res2 = router.run_router("Thủ tục phạt vi phạm nồng độ cồn xe máy", thread_id=thread_id)
        assert res2["status"] == "verified"
        assert len(res2["results"]) == 1
        assert "Nghị định 168/2024/NĐ-CP" in res2["answer"]

        # Checkpoint state now has 4 messages (accumulated across turns 1 and 2)
        state2 = graph.get_state({"configurable": {"thread_id": thread_id}})
        assert len(state2.values.get("messages", [])) == 4
        assert state2.values["messages"][2]["role"] == "user"
        assert "nồng độ cồn" in state2.values["messages"][2]["content"]
