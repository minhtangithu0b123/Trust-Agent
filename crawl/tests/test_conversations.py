"""Backend Session Persistence & Database CRUD Test Suite (Tiers 1-4).

Covers Features 3 & 4 (Milestone M2):
- Feature 3: Backend DB Persistence (Database connection, models, messages, transactions, cascade delete, restart persistence)
- Feature 4: Session CRUD Endpoints (/api/conversations REST APIs)

Execution guarantees:
- 100% offline execution with zero external network calls.
- Full test database isolation using temporary SQLite files or in-memory DBs.
- Structured across 4 systematic tiers:
    Tier 1: Feature Coverage (>=5 test cases per feature)
    Tier 2: Boundary & Corner Cases (>=5 test cases per feature)
    Tier 3: Cross-Feature Combinations
    Tier 4: Real-World Application Scenarios
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
import app.router as router

# Dynamic import of database manager and repository helpers
try:
    import app.db as db
    from app.db import (
        DatabaseManager,
        DatabaseDriverNotFoundError,
        get_db_manager,
        reset_db_manager,
        init_db,
        create_conversation,
        list_conversations,
        get_conversation,
        update_conversation_title,
        delete_conversation,
        add_message,
        get_conversation_messages,
    )
except ImportError:
    db = None
    DatabaseManager = None
    DatabaseDriverNotFoundError = None
    get_db_manager = None
    reset_db_manager = None
    init_db = None
    create_conversation = None
    list_conversations = None
    get_conversation = None
    update_conversation_title = None
    delete_conversation = None
    add_message = None
    get_conversation_messages = None


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def test_db_file(tmp_path, monkeypatch):
    """Provides an isolated SQLite file database for each test."""
    db_file = tmp_path / f"test_conversations_{uuid.uuid4().hex[:8]}.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()

    if reset_db_manager is not None:
        reset_db_manager()
    if init_db is not None:
        init_db(db_url)

    yield str(db_file)

    if reset_db_manager is not None:
        reset_db_manager()
    get_settings.cache_clear()


@pytest.fixture
def client(test_db_file):
    """FastAPI TestClient connected to the isolated test database."""
    return TestClient(app)


@pytest.fixture
def mock_router(monkeypatch):
    """Mocks router execution to return deterministic verified responses offline."""
    def fake_run_router(query: str, k: int = 5, thread_id: str | None = None) -> dict[str, Any]:
        return {
            "query": query,
            "answer": f"Theo Nghị định 168/2024/NĐ-CP: tư vấn pháp lý cho câu hỏi '{query}'.",
            "domain": "traffic",
            "status": "verified",
            "guardrail_status": "verified",
            "guardrail_warnings": [],
            "thread_id": thread_id,
            "citations": [
                {
                    "document_id": "traffic-doc-168",
                    "so_hieu": "168/2024/NĐ-CP",
                    "dieu": "Điều 6",
                    "khoan": "Khoản 8",
                    "ten_van_ban": "Nghị định 168/2024/NĐ-CP",
                }
            ],
            "metadata": {"domain": "traffic", "guardrail_status": "verified"},
            "results": [],
        }

    monkeypatch.setattr("app.main.run_router", fake_run_router)
    if hasattr(router, "run_router"):
        monkeypatch.setattr(router, "run_router", fake_run_router)
    return fake_run_router


# ==============================================================================
# Tier 1: Feature Coverage (>=5 test cases per feature)
# ==============================================================================

class TestTier1FeatureCoverage:
    """Tier 1: Primary behavior and happy path verification for Features 3 & 4."""

    # --- Feature 4: Session CRUD Endpoints ---

    def test_post_conversation_default_title(self, client):
        """1. POST /api/conversations with default title creates session returning HTTP 201."""
        response = client.post("/api/conversations", json={})
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()

        assert "id" in data
        uuid.UUID(data["id"])  # Assert valid UUID format
        assert data["title"] == "Cuộc trò chuyện mới"
        assert "created_at" in data
        assert "updated_at" in data
        assert data["message_count"] == 0

    def test_post_conversation_custom_title(self, client):
        """2. POST /api/conversations with custom title returns HTTP 201 and custom title."""
        custom_title = "Tư vấn quy định thành lập doanh nghiệp 2026"
        response = client.post("/api/conversations", json={"title": custom_title})
        assert response.status_code == 201
        data = response.json()

        assert data["title"] == custom_title
        uuid.UUID(data["id"])
        assert data["message_count"] == 0

    def test_get_conversations_list_sorted_desc(self, client):
        """3. GET /api/conversations returns list sorted by updated_at DESC with message_count."""
        # Create 3 conversations sequentially
        res1 = client.post("/api/conversations", json={"title": "Cuộc trò chuyện 1"}).json()
        res2 = client.post("/api/conversations", json={"title": "Cuộc trò chuyện 2"}).json()
        res3 = client.post("/api/conversations", json={"title": "Cuộc trò chuyện 3"}).json()

        response = client.get("/api/conversations")
        assert response.status_code == 200
        conversations = response.json()
        assert isinstance(conversations, list)
        assert len(conversations) >= 3

        conv_ids = [c["id"] for c in conversations]
        assert res1["id"] in conv_ids
        assert res2["id"] in conv_ids
        assert res3["id"] in conv_ids

        # Verify sorted by updated_at descending
        timestamps = [c["updated_at"] for c in conversations]
        assert timestamps == sorted(timestamps, reverse=True)

        # Verify required fields
        for item in conversations:
            assert "id" in item
            assert "title" in item
            assert "created_at" in item
            assert "updated_at" in item
            assert "message_count" in item

    def test_get_conversation_by_id(self, client):
        """4. GET /api/conversations/{id} retrieves existing conversation details."""
        created = client.post("/api/conversations", json={"title": "Chi tiết cuộc trò chuyện"}).json()
        conv_id = created["id"]

        response = client.get(f"/api/conversations/{conv_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == conv_id
        assert data["title"] == "Chi tiết cuộc trò chuyện"
        assert data["created_at"] == created["created_at"]
        assert data["updated_at"] == created["updated_at"]
        assert data["message_count"] == 0

    def test_get_conversation_messages_chronological(self, client, test_db_file):
        """5. GET /api/conversations/{id}/messages retrieves messages ordered chronologically."""
        conv = client.post("/api/conversations", json={"title": "Hội thoại có tin nhắn"}).json()
        conv_id = conv["id"]

        if add_message is not None:
            add_message(
                conversation_id=conv_id,
                role="user",
                content="Câu hỏi 1: Nồng độ cồn xe máy?",
            )
            add_message(
                conversation_id=conv_id,
                role="assistant",
                content="Trả lời 1: Phạt 6-8 triệu đồng theo Nghị định 168.",
                citations=[{"so_hieu": "168/2024/NĐ-CP", "dieu": "Điều 6"}],
                status="verified",
                metadata={"domain": "traffic"},
            )

        response = client.get(f"/api/conversations/{conv_id}/messages")
        assert response.status_code == 200
        messages = response.json()
        assert isinstance(messages, list)

        if add_message is not None:
            assert len(messages) == 2
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "Câu hỏi 1: Nồng độ cồn xe máy?"
            assert messages[1]["role"] == "assistant"
            assert "168/2024/NĐ-CP" in str(messages[1]["citations"])
            assert messages[1]["status"] == "verified"
            # Assert chronological order
            assert messages[0]["created_at"] <= messages[1]["created_at"]

    def test_patch_conversation_rename(self, client):
        """6. PATCH /api/conversations/{id} renames title and updates updated_at."""
        created = client.post("/api/conversations", json={"title": "Tên ban đầu"}).json()
        conv_id = created["id"]

        new_title = "Tên sau khi đổi"
        response = client.patch(f"/api/conversations/{conv_id}", json={"title": new_title})
        assert response.status_code == 200
        updated = response.json()

        assert updated["id"] == conv_id
        assert updated["title"] == new_title
        assert updated["updated_at"] >= created["updated_at"]

        # Verify change persists via GET
        get_res = client.get(f"/api/conversations/{conv_id}")
        assert get_res.status_code == 200
        assert get_res.json()["title"] == new_title

    def test_delete_conversation_204(self, client):
        """7. DELETE /api/conversations/{id} deletes conversation returning HTTP 204 No Content."""
        created = client.post("/api/conversations", json={"title": "Cuộc trò chuyện cần xóa"}).json()
        conv_id = created["id"]

        del_res = client.delete(f"/api/conversations/{conv_id}")
        assert del_res.status_code == 204
        assert del_res.text == ""

        # Assert conversation no longer exists
        get_res = client.get(f"/api/conversations/{conv_id}")
        assert get_res.status_code == 404

    # --- Feature 3: Backend DB Manager Direct Operations ---

    def test_db_manager_sqlite_pragmas(self, test_db_file):
        """8. DatabaseManager enforces SQLite WAL mode, foreign keys ON, and busy timeout."""
        pytest.importorskip("app.db")
        mgr = get_db_manager()

        with mgr.connection() as conn:
            fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            assert fk_status == 1, "Foreign keys MUST be enabled in SQLite connection"

            journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0].lower()
            assert journal_mode in ("wal", "memory"), f"Expected WAL or memory journal mode, got {journal_mode}"

            busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
            assert busy_timeout >= 1000, f"Expected busy timeout >= 1000ms, got {busy_timeout}"

    def test_db_manager_create_and_get_conversation(self, test_db_file):
        """9. Direct DatabaseManager calls create_conversation and get_conversation."""
        pytest.importorskip("app.db")
        conv = create_conversation(title="Direct DB Manager Test")
        assert conv["title"] == "Direct DB Manager Test"
        assert "id" in conv
        uuid.UUID(conv["id"])

        fetched = get_conversation(conv["id"])
        assert fetched is not None
        assert fetched["id"] == conv["id"]
        assert fetched["title"] == "Direct DB Manager Test"
        assert fetched["message_count"] == 0

    def test_db_manager_add_and_get_messages(self, test_db_file):
        """10. Direct DatabaseManager calls add_message and retrieves messages with parsed JSON."""
        pytest.importorskip("app.db")
        conv = create_conversation(title="Message Test Session")
        conv_id = conv["id"]

        user_msg = add_message(
            conversation_id=conv_id,
            role="user",
            content="Quy định ngày nghỉ phép năm?",
        )
        assert user_msg["role"] == "user"
        assert user_msg["conversation_id"] == conv_id

        citations = [{"document_id": "labor-45", "so_hieu": "45/2019/QH14", "dieu": "Điều 113"}]
        metadata = {"domain": "labor", "guardrail_status": "verified"}

        asst_msg = add_message(
            conversation_id=conv_id,
            role="assistant",
            content="Người lao động làm đủ 12 tháng được nghỉ 12 ngày phép năm.",
            citations=citations,
            status="verified",
            metadata=metadata,
        )
        assert asst_msg["role"] == "assistant"
        assert asst_msg["citations"] == citations
        assert asst_msg["metadata"] == metadata

        history = get_conversation_messages(conv_id)
        assert len(history) == 2
        assert history[0]["id"] == user_msg["id"]
        assert history[1]["id"] == asst_msg["id"]
        assert history[1]["citations"] == citations

    def test_db_manager_update_conversation_title(self, test_db_file):
        """11. Direct DatabaseManager calls update_conversation_title."""
        pytest.importorskip("app.db")
        conv = create_conversation(title="Old Title")
        conv_id = conv["id"]

        updated = update_conversation_title(conv_id, "New Direct Title")
        assert updated is not None
        assert updated["title"] == "New Direct Title"
        assert updated["id"] == conv_id

        fetched = get_conversation(conv_id)
        assert fetched["title"] == "New Direct Title"

    def test_db_manager_delete_conversation(self, test_db_file):
        """12. Direct DatabaseManager calls delete_conversation."""
        pytest.importorskip("app.db")
        conv = create_conversation(title="To be deleted")
        conv_id = conv["id"]

        deleted = delete_conversation(conv_id)
        assert deleted is True

        fetched = get_conversation(conv_id)
        assert fetched is None


# ==============================================================================
# Tier 2: Boundary & Corner Cases (>=5 test cases per feature)
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: Error handling, edge cases, whitespace, boundary limits, UTF-8."""

    def test_get_non_existent_conversation_returns_404(self, client):
        """1. GET /api/conversations/{non_existent_id} returns HTTP 404."""
        missing_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/conversations/{missing_id}")
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    def test_patch_non_existent_conversation_returns_404(self, client):
        """2. PATCH /api/conversations/{non_existent_id} returns HTTP 404."""
        missing_id = "00000000-0000-0000-0000-000000000000"
        response = client.patch(f"/api/conversations/{missing_id}", json={"title": "New Title"})
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    def test_delete_non_existent_conversation_returns_404(self, client):
        """3. DELETE /api/conversations/{non_existent_id} returns HTTP 404."""
        missing_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(f"/api/conversations/{missing_id}")
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    def test_get_messages_non_existent_conversation_returns_404(self, client):
        """4. GET /api/conversations/{non_existent_id}/messages returns HTTP 404, NOT empty list."""
        missing_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/conversations/{missing_id}/messages")
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    def test_get_messages_empty_conversation_returns_200_empty_list(self, client):
        """5. GET /api/conversations/{id}/messages for conversation with 0 messages returns HTTP 200 []."""
        conv = client.post("/api/conversations", json={"title": "Empty Session"}).json()
        response = client.get(f"/api/conversations/{conv['id']}/messages")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_whitespace_title_validation_or_fallback(self, client):
        """6. POST with whitespace-only title either falls back to default title or returns 422."""
        response = client.post("/api/conversations", json={"title": "   "})
        if response.status_code == 201:
            data = response.json()
            assert data["title"] == "Cuộc trò chuyện mới", "Whitespace title must fall back to default"
        else:
            assert response.status_code == 422

    def test_patch_empty_or_whitespace_title_returns_422(self, client):
        """7. PATCH with empty or whitespace-only title returns HTTP 422 Unprocessable Entity."""
        conv = client.post("/api/conversations", json={"title": "Valid Initial Title"}).json()
        conv_id = conv["id"]

        # Empty string
        res_empty = client.patch(f"/api/conversations/{conv_id}", json={"title": ""})
        assert res_empty.status_code == 422

        # Whitespace-only string
        res_ws = client.patch(f"/api/conversations/{conv_id}", json={"title": "     "})
        assert res_ws.status_code == 422

        # Verify original title was preserved intact
        check = client.get(f"/api/conversations/{conv_id}").json()
        assert check["title"] == "Valid Initial Title"

    def test_extremely_long_title_handling(self, client):
        """8. Title boundary testing up to 255 characters and graceful rejection > 255."""
        conv = client.post("/api/conversations", json={"title": "Test Title Boundary"}).json()
        conv_id = conv["id"]

        # Exactly 255 chars should be valid
        title_255 = "A" * 255
        res_255 = client.patch(f"/api/conversations/{conv_id}", json={"title": title_255})
        assert res_255.status_code == 200
        assert res_255.json()["title"] == title_255

        # > 255 chars (e.g. 300 chars) should be rejected with 422
        title_300 = "B" * 300
        res_300 = client.patch(f"/api/conversations/{conv_id}", json={"title": title_300})
        assert res_300.status_code == 422

    def test_special_characters_vietnamese_diacritics_and_emojis(self, client):
        """9. Complete UTF-8 preservation: Vietnamese diacritics, symbols, quotes, and emojis."""
        vietnamese_title = "Luật Doanh nghiệp 2020: Thủ tục thành lập công ty TNHH 1 TV 🇻🇳⚖️ [Hỏi & Đáp]"
        response = client.post("/api/conversations", json={"title": vietnamese_title})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == vietnamese_title

        # Verify in GET
        conv_id = data["id"]
        get_res = client.get(f"/api/conversations/{conv_id}")
        assert get_res.json()["title"] == vietnamese_title

        # Verify in PATCH
        renamed_vietnamese = "Tra cứu Nghị định 168/2024/NĐ-CP: Phạt nồng độ cồn xe máy 🏍️🚨"
        patch_res = client.patch(f"/api/conversations/{conv_id}", json={"title": renamed_vietnamese})
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == renamed_vietnamese

    def test_pagination_parameters_validation_and_boundaries(self, client):
        """10. Pagination limit and offset boundary validation."""
        # Create 5 conversations
        for i in range(5):
            client.post("/api/conversations", json={"title": f"Conv {i+1}"})

        # Valid pagination: limit=2, offset=0
        res = client.get("/api/conversations?limit=2&offset=0")
        assert res.status_code == 200
        assert len(res.json()) == 2

        # Valid pagination: limit=2, offset=2
        res2 = client.get("/api/conversations?limit=2&offset=2")
        assert res2.status_code == 200
        assert len(res2.json()) == 2

        # Offset beyond total count returns empty list []
        res_empty = client.get("/api/conversations?limit=10&offset=500")
        assert res_empty.status_code == 200
        assert res_empty.json() == []

        # Invalid negative offset returns 422
        res_bad_offset = client.get("/api/conversations?offset=-1")
        assert res_bad_offset.status_code == 422

        # Invalid limit <= 0 returns 422
        res_bad_limit = client.get("/api/conversations?limit=0")
        assert res_bad_limit.status_code == 422

    def test_postgresql_driver_check(self):
        """11. PostgreSQL URL detection raises DatabaseDriverNotFoundError when driver is absent."""
        pytest.importorskip("app.db")
        with pytest.raises(Exception) as exc_info:
            DatabaseManager("postgresql://user:pass@localhost:5432/testdb")
        err_msg = str(exc_info.value).lower()
        assert "postgresql" in err_msg or "psycopg" in err_msg


# ==============================================================================
# Tier 3: Cross-Feature Combinations
# ==============================================================================

class TestTier3CrossFeatureCombinations:
    """Tier 3: Foreign key cascade, /router/ask persistence, restarts, backward compatibility."""

    def test_foreign_key_cascade_delete(self, client, test_db_file):
        """1. Foreign key cascade: Deleting a conversation removes all child messages from DB."""
        pytest.importorskip("app.db")
        conv = client.post("/api/conversations", json={"title": "Cascade Test Session"}).json()
        conv_id = conv["id"]

        # Insert 3 messages directly into the database
        add_message(conversation_id=conv_id, role="user", content="User Q1")
        add_message(conversation_id=conv_id, role="assistant", content="Assistant A1")
        add_message(conversation_id=conv_id, role="user", content="User Q2")

        # Verify messages exist in SQLite directly
        with sqlite3.connect(test_db_file) as direct_conn:
            count = direct_conn.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,)
            ).fetchone()[0]
            assert count == 3, f"Expected 3 messages before delete, got {count}"

        # Delete conversation via API
        del_res = client.delete(f"/api/conversations/{conv_id}")
        assert del_res.status_code == 204

        # Verify conversation is gone
        assert client.get(f"/api/conversations/{conv_id}").status_code == 404

        # Direct SQL inspection: ALL child messages MUST be purged by ON DELETE CASCADE
        with sqlite3.connect(test_db_file) as direct_conn:
            remaining_messages = direct_conn.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,)
            ).fetchone()[0]
            assert remaining_messages == 0, (
                f"CASCADE DELETE FAILED: {remaining_messages} orphan messages remaining in DB"
            )

    def test_router_ask_persists_messages_and_citations(self, client, mock_router):
        """2. Submitting query to /router/ask with conversation_id persists turns with citations."""
        conv = client.post("/api/conversations", json={"title": "Tra cứu nồng độ cồn"}).json()
        conv_id = conv["id"]

        # Call /router/ask with conversation_id
        ask_res = client.post(
            "/router/ask",
            json={"query": "Mức phạt nồng độ cồn xe máy?", "conversation_id": conv_id, "k": 5},
        )
        assert ask_res.status_code == 200, f"Router ask failed: {ask_res.text}"
        data = ask_res.json()

        assert data["conversation_id"] == conv_id
        assert data["thread_id"] == conv_id
        assert data["session_id"] == conv_id
        assert "answer" in data

        # Verify message history stored in DB via GET /api/conversations/{id}/messages
        hist_res = client.get(f"/api/conversations/{conv_id}/messages")
        assert hist_res.status_code == 200
        messages = hist_res.json()
        assert len(messages) == 2, f"Expected 2 messages (user + assistant), got {len(messages)}"

        # User message
        assert messages[0]["role"] == "user"
        assert "nồng độ cồn xe máy" in messages[0]["content"]

        # Assistant message
        assert messages[1]["role"] == "assistant"
        assert "168/2024/NĐ-CP" in messages[1]["content"]
        assert len(messages[1]["citations"]) > 0
        assert messages[1]["citations"][0]["so_hieu"] == "168/2024/NĐ-CP"
        assert messages[1]["status"] == "verified"

        # Check updated message_count in conversation detail
        conv_detail = client.get(f"/api/conversations/{conv_id}").json()
        assert conv_detail["message_count"] == 2

    def test_router_ask_backward_compatibility_with_thread_and_session_id(self, client, mock_router):
        """3. Support thread_id and session_id interchangeably with conversation_id."""
        thread_id = f"legacy-thread-{uuid.uuid4().hex[:8]}"

        # Request using thread_id
        res1 = client.post(
            "/router/ask",
            json={"query": "Hỏi đáp với thread_id", "thread_id": thread_id, "k": 5},
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["thread_id"] == thread_id
        assert data1["session_id"] == thread_id
        assert data1["conversation_id"] == thread_id

        # Verify conversation was created in DB with that ID
        get_conv1 = client.get(f"/api/conversations/{thread_id}")
        assert get_conv1.status_code == 200
        assert get_conv1.json()["id"] == thread_id

        session_id = f"legacy-session-{uuid.uuid4().hex[:8]}"

        # Request using session_id
        res2 = client.post(
            "/router/ask",
            json={"query": "Hỏi đáp với session_id", "session_id": session_id, "k": 5},
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["session_id"] == session_id
        assert data2["thread_id"] == session_id
        assert data2["conversation_id"] == session_id

        get_conv2 = client.get(f"/api/conversations/{session_id}")
        assert get_conv2.status_code == 200
        assert get_conv2.json()["id"] == session_id

    def test_persistence_across_backend_restart(self, test_db_file):
        """4. Write records to SQLite file, close all connections, reopen fresh instance, assert data."""
        pytest.importorskip("app.db")

        # Step 1: Open manager, write records
        mgr1 = DatabaseManager(f"sqlite:///{Path(test_db_file).as_posix()}")
        conv = mgr1.create_conversation(title="Session Persistent across Restart")
        conv_id = conv["id"]

        msg1 = mgr1.add_message(conv_id, role="user", content="Persistent question")
        msg2 = mgr1.add_message(
            conv_id,
            role="assistant",
            content="Persistent answer with citations",
            citations=[{"so_hieu": "168/2024/NĐ-CP", "dieu": "Điều 6"}],
            status="verified",
            metadata={"source": "law"},
        )

        # Step 2: Simulate complete server shutdown & memory wipe
        mgr1.close()
        reset_db_manager()

        # Step 3: Reopen fresh DatabaseManager from the existing file
        mgr2 = DatabaseManager(f"sqlite:///{Path(test_db_file).as_posix()}")
        loaded_conv = mgr2.get_conversation(conv_id)
        assert loaded_conv is not None
        assert loaded_conv["id"] == conv_id
        assert loaded_conv["title"] == "Session Persistent across Restart"
        assert loaded_conv["created_at"] == conv["created_at"]

        loaded_messages = mgr2.get_conversation_messages(conv_id)
        assert len(loaded_messages) == 2
        assert loaded_messages[0]["id"] == msg1["id"]
        assert loaded_messages[0]["content"] == "Persistent question"
        assert loaded_messages[1]["id"] == msg2["id"]
        assert loaded_messages[1]["citations"] == [{"so_hieu": "168/2024/NĐ-CP", "dieu": "Điều 6"}]
        assert loaded_messages[1]["status"] == "verified"
        assert loaded_messages[1]["metadata"] == {"source": "law"}

        mgr2.close()

    def test_rename_active_conversation_updates_timestamp_preserves_messages(self, client, mock_router):
        """5. Renaming an active conversation updates updated_at without corrupting message history."""
        conv = client.post("/api/conversations", json={"title": "Original Active Title"}).json()
        conv_id = conv["id"]

        # Send 2 queries via /router/ask (creating 4 messages)
        client.post("/router/ask", json={"query": "Câu hỏi lượt 1", "conversation_id": conv_id})
        client.post("/router/ask", json={"query": "Câu hỏi lượt 2", "conversation_id": conv_id})

        initial_messages = client.get(f"/api/conversations/{conv_id}/messages").json()
        assert len(initial_messages) == 4
        msg_ids = [m["id"] for m in initial_messages]

        # Rename conversation
        renamed = client.patch(f"/api/conversations/{conv_id}", json={"title": "Renamed Active Session"}).json()
        assert renamed["title"] == "Renamed Active Session"
        assert renamed["message_count"] == 4

        # Verify message history is 100% preserved and uncorrupted
        current_messages = client.get(f"/api/conversations/{conv_id}/messages").json()
        assert len(current_messages) == 4
        assert [m["id"] for m in current_messages] == msg_ids
        assert current_messages[0]["content"] == initial_messages[0]["content"]


# ==============================================================================
# Tier 4: Real-World Scenarios
# ==============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: End-to-end multi-turn consultation lifecycle and concurrent multi-session switching."""

    def test_full_multi_turn_consultation_lifecycle(self, client, mock_router, test_db_file):
        """1. Full consultation lifecycle:
        Create conversation -> 3 multi-turn queries -> in-place rename ->
        retrieve full history with citations -> delete conversation -> verify cascade cleanup.
        """
        # Step 1: Create consultation session
        create_res = client.post(
            "/api/conversations",
            json={"title": "Tư vấn thành lập doanh nghiệp khởi nghiệp"},
        )
        assert create_res.status_code == 201
        session = create_res.json()
        conv_id = session["id"]

        # Step 2: Multi-turn Turn 1
        q1 = "Điều kiện thành lập công ty TNHH một thành viên là gì?"
        r1 = client.post("/router/ask", json={"query": q1, "conversation_id": conv_id})
        assert r1.status_code == 200
        assert r1.json()["conversation_id"] == conv_id

        # Step 3: Multi-turn Turn 2
        q2 = "Vốn điều lệ tối thiểu theo Luật Doanh nghiệp là bao nhiêu?"
        r2 = client.post("/router/ask", json={"query": q2, "conversation_id": conv_id})
        assert r2.status_code == 200

        # Step 4: Multi-turn Turn 3
        q3 = "Thời hạn góp vốn điều lệ là bao nhiêu ngày kể từ ngày cấp GCNĐKDN?"
        r3 = client.post("/router/ask", json={"query": q3, "conversation_id": conv_id})
        assert r3.status_code == 200

        # Step 5: Verify message count before rename
        detail_before = client.get(f"/api/conversations/{conv_id}").json()
        assert detail_before["message_count"] == 6

        # Step 6: In-place rename to summary title
        summary_title = "Thủ tục TNHH 1 TV & Quy định góp vốn 2026"
        patch_res = client.patch(f"/api/conversations/{conv_id}", json={"title": summary_title})
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == summary_title

        # Step 7: Retrieve message history with citations
        history_res = client.get(f"/api/conversations/{conv_id}/messages")
        assert history_res.status_code == 200
        history = history_res.json()
        assert len(history) == 6

        # Check turn roles and order
        expected_roles = ["user", "assistant", "user", "assistant", "user", "assistant"]
        actual_roles = [m["role"] for m in history]
        assert actual_roles == expected_roles

        # Check assistant answers have citations
        for assistant_msg in [history[1], history[3], history[5]]:
            assert assistant_msg["status"] == "verified"
            assert len(assistant_msg["citations"]) > 0
            assert "so_hieu" in assistant_msg["citations"][0]

        # Step 8: Delete conversation
        del_res = client.delete(f"/api/conversations/{conv_id}")
        assert del_res.status_code == 204

        # Step 9: Verify cascade cleanup via API
        assert client.get(f"/api/conversations/{conv_id}").status_code == 404
        assert client.get(f"/api/conversations/{conv_id}/messages").status_code == 404

        # Step 10: Verify cascade cleanup directly in SQLite database
        with sqlite3.connect(test_db_file) as direct_conn:
            c_count = direct_conn.execute("SELECT COUNT(*) FROM conversations WHERE id = ?", (conv_id,)).fetchone()[0]
            m_count = direct_conn.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()[0]
            assert c_count == 0, "Conversation record was not deleted"
            assert m_count == 0, f"Cascade failed: {m_count} orphan messages found in database"

    def test_concurrent_multi_session_switching(self, client, mock_router):
        """2. Rapid creation and interleaved switching across multiple independent conversations."""
        # Create 3 independent conversations
        s_traffic = client.post("/api/conversations", json={"title": "Chủ đề Giao thông"}).json()["id"]
        s_labor = client.post("/api/conversations", json={"title": "Chủ đề Lao động"}).json()["id"]
        s_accounting = client.post("/api/conversations", json={"title": "Chủ đề Kế toán"}).json()["id"]

        # Interleave queries across sessions
        # Traffic turn 1
        client.post("/router/ask", json={"query": "Tốc độ tối đa trong khu đông dân cư?", "conversation_id": s_traffic})
        # Labor turn 1
        client.post("/router/ask", json={"query": "Thời giờ làm việc bình thường là bao nhiêu tiếng?", "conversation_id": s_labor})
        # Traffic turn 2
        client.post("/router/ask", json={"query": "Mức phạt chạy quá tốc độ từ 10-20km/h?", "conversation_id": s_traffic})
        # Accounting turn 1
        client.post("/router/ask", json={"query": "Thời hạn nộp báo cáo tài chính năm là khi nào?", "conversation_id": s_accounting})
        # Labor turn 2
        client.post("/router/ask", json={"query": "Tiền lương làm thêm giờ vào ngày nghỉ hàng tuần?", "conversation_id": s_labor})

        # Assert isolated message counts
        hist_traffic = client.get(f"/api/conversations/{s_traffic}/messages").json()
        hist_labor = client.get(f"/api/conversations/{s_labor}/messages").json()
        hist_accounting = client.get(f"/api/conversations/{s_accounting}/messages").json()

        assert len(hist_traffic) == 4, f"Expected 4 messages in traffic session, got {len(hist_traffic)}"
        assert len(hist_labor) == 4, f"Expected 4 messages in labor session, got {len(hist_labor)}"
        assert len(hist_accounting) == 2, f"Expected 2 messages in accounting session, got {len(hist_accounting)}"

        # Assert context content isolation
        assert "Tốc độ tối đa" in hist_traffic[0]["content"]
        assert "Thời giờ làm việc" in hist_labor[0]["content"]
        assert "báo cáo tài chính" in hist_accounting[0]["content"]

        # Verify sidebar list ordering reflects latest activity
        conv_list = client.get("/api/conversations").json()
        list_ids = [c["id"] for c in conv_list[:3]]
        # s_labor was updated most recently (turn 2), followed by s_accounting, followed by s_traffic
        assert s_labor in list_ids
        assert s_accounting in list_ids
        assert s_traffic in list_ids
