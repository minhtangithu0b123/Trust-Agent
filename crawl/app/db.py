"""Database Manager and Connection Factory for Trust-AGENT session persistence.

Supports SQLite (standard library) with WAL mode, foreign key enforcement,
and busy timeout by default, with PostgreSQL readiness via DATABASE_URL.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from .config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DatabaseError(Exception):
    """Base exception for all database layer operations."""


class DatabaseConfigurationError(DatabaseError):
    """Raised when database configuration or connection parameters are invalid."""


class DatabaseDriverNotFoundError(DatabaseConfigurationError, RuntimeError):
    """Raised when a configured database backend driver is not installed."""


class ConversationNotFoundError(DatabaseError):
    """Raised when an operation targets a non-existent conversation."""


# ---------------------------------------------------------------------------
# Pydantic Schemas for REST API & Repository Contracts
# ---------------------------------------------------------------------------

class ConversationCreate(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Tiêu đề cuộc trò chuyện (tùy chọn, tối đa 255 ký tự).",
    )

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None


class ConversationUpdate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
        description="Tiêu đề mới của cuộc trò chuyện (1-255 ký tự, không được để trống).",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Tiêu đề không được để trống hoặc chỉ chứa khoảng trắng.")
        return stripped


class ConversationDetail(BaseModel):
    id: str = Field(description="UUID định danh cuộc trò chuyện")
    title: str = Field(description="Tiêu đề cuộc trò chuyện")
    created_at: str = Field(description="Thời gian tạo theo định dạng ISO 8601 UTC")
    updated_at: str = Field(description="Thời gian cập nhật gần nhất theo định dạng ISO 8601 UTC")
    message_count: int = Field(default=0, description="Tổng số tin nhắn trong cuộc trò chuyện")


class ConversationSummary(BaseModel):
    id: str = Field(description="UUID định danh cuộc trò chuyện")
    title: str = Field(description="Tiêu đề cuộc trò chuyện")
    created_at: str = Field(description="Thời gian tạo theo định dạng ISO 8601 UTC")
    updated_at: str = Field(description="Thời gian cập nhật gần nhất theo định dạng ISO 8601 UTC")
    message_count: int = Field(default=0, description="Tổng số tin nhắn trong cuộc trò chuyện")
    last_message: str | None = Field(default=None, description="Trích đoạn nội dung tin nhắn gần nhất")


class MessageDetail(BaseModel):
    id: str = Field(description="UUID định danh tin nhắn")
    conversation_id: str = Field(description="ID cuộc trò chuyện chứa tin nhắn")
    role: str = Field(description="Vai trò người gửi (user/assistant/system)")
    content: str = Field(description="Nội dung văn bản tin nhắn")
    citations: list[dict[str, Any]] = Field(default_factory=list, description="Danh sách các trích dẫn pháp lý")
    status: str | None = Field(default=None, description="Trạng thái câu trả lời")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata mở rộng")
    created_at: str = Field(description="Thời gian tạo tin nhắn theo định dạng ISO 8601 UTC")


# ---------------------------------------------------------------------------
# Helper: URL Parsing & SQLite Path Resolution
# ---------------------------------------------------------------------------

def parse_sqlite_path(db_url: str) -> str:
    """Extract a valid filesystem path or :memory: from a SQLite database URL."""
    if not db_url or db_url in (":memory:", "sqlite:///:memory:"):
        return ":memory:"
    if db_url.startswith("sqlite://"):
        raw = db_url[len("sqlite://") :]
        if raw in (":memory:", "/:memory:"):
            return ":memory:"
        # Windows drive letter (e.g. /C:/path or /C:\path)
        if len(raw) >= 3 and raw[0] == "/" and raw[2] == ":":
            raw = raw[1:]
        elif raw.startswith("///"):
            raw = raw[3:]
        elif raw.startswith("/."):
            raw = raw[1:]
        elif raw.startswith("/"):
            raw = raw[1:]
        return raw
    return db_url


def adapt_sql(sql: str, dialect: str) -> str:
    """Adapt standard parameter placeholders ('?') to target dialect."""
    if dialect in ("postgres", "postgresql"):
        return sql.replace("?", "%s")
    return sql


# ---------------------------------------------------------------------------
# Database Manager & Connection Factory
# ---------------------------------------------------------------------------

class DatabaseManager:
    """Connection manager supporting SQLite (default) and PostgreSQL."""

    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url or get_settings().database_url
        self.parsed_url = urlparse(self.db_url)
        scheme = self.parsed_url.scheme.lower()
        if scheme in ("postgresql", "postgres"):
            self.dialect = "postgresql"
            self.is_memory = False
            self._anchor_conn = None
            self.sqlite_path = ""
            self.db_path = None
        else:
            self.dialect = "sqlite"
            sqlite_target = parse_sqlite_path(self.db_url)
            self.is_memory = (sqlite_target == ":memory:")
            self.sqlite_path = sqlite_target
            self._anchor_conn = None

            if self.is_memory:
                self.shared_uri = f"file:trust_agent_mem_{id(self)}?mode=memory&cache=shared"
                self._anchor_conn = sqlite3.connect(self.shared_uri, uri=True, timeout=5.0)
                self._anchor_conn.execute("PRAGMA foreign_keys = ON;")
                self.db_path = Path(":memory:")
            else:
                self.shared_uri = ""
                file_path = Path(self.sqlite_path)
                if not file_path.is_absolute():
                    file_path = get_settings().resolve_path(self.sqlite_path)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                self.sqlite_path = str(file_path)
                self.db_path = file_path

        self.init_db()

    def get_raw_connection(self) -> Any:
        """Create and configure a fresh database connection."""
        if self.dialect == "sqlite":
            target = self.shared_uri if self.is_memory else self.sqlite_path
            is_uri = bool(self.is_memory)
            conn = sqlite3.connect(
                target,
                timeout=5.0,
                check_same_thread=False,
                uri=is_uri,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            return conn

        # PostgreSQL factory
        try:
            import psycopg  # type: ignore
            from psycopg.rows import dict_row  # type: ignore
            return psycopg.connect(self.db_url, row_factory=dict_row)
        except ImportError:
            try:
                import psycopg2  # type: ignore
                from psycopg2.extras import RealDictCursor  # type: ignore
                return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
            except ImportError as exc:
                safe_url = f"{self.parsed_url.scheme}://{self.parsed_url.hostname or 'localhost'}{self.parsed_url.path}"
                raise DatabaseDriverNotFoundError(
                    f"PostgreSQL database URL configured ('{safe_url}'), but neither 'psycopg' "
                    "nor 'psycopg2' is installed. In an offline environment, please configure a "
                    "SQLite database URL (e.g. 'sqlite:///./data/conversations.db') or install psycopg."
                ) from exc

    @contextmanager
    def connection(self) -> Iterator[Any]:
        """Context manager providing an isolated, thread-safe connection."""
        conn = self.get_raw_connection()
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception as exc:
                logger.warning("Error closing database connection: %s", exc)

    def init_db(self) -> None:
        """Create tables and indexes idempotently if they do not exist."""
        ddl_conversations = """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """
        ddl_messages = """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                citations TEXT,
                status TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            );
        """
        idx_messages = "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id, created_at ASC);"
        idx_conversations = "CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations (updated_at DESC);"

        with self.connection() as conn:
            with conn:
                conn.execute(adapt_sql(ddl_conversations, self.dialect))
                conn.execute(adapt_sql(ddl_messages, self.dialect))
                conn.execute(adapt_sql(idx_messages, self.dialect))
                conn.execute(adapt_sql(idx_conversations, self.dialect))

    def create_conversation(
        self,
        title: str | None = None,
        conversation_id: str | None = None,
        conn: Any | None = None,
    ) -> dict[str, Any]:
        cid = conversation_id or str(uuid.uuid4())
        ctitle = (title or "Cuộc trò chuyện mới").strip() or "Cuộc trò chuyện mới"
        now = datetime.now(UTC).isoformat()

        def _execute(target_conn: Any) -> dict[str, Any]:
            with target_conn:
                sql = adapt_sql(
                    "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    self.dialect,
                )
                target_conn.execute(sql, (cid, ctitle, now, now))
            return {
                "id": cid,
                "title": ctitle,
                "created_at": now,
                "updated_at": now,
                "message_count": 0,
            }

        if conn is not None:
            return _execute(conn)
        with self.connection() as connection:
            return _execute(connection)

    def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
        conn: Any | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        sql = adapt_sql(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) AS message_count,
                   (SELECT m2.content FROM messages m2 WHERE m2.conversation_id = c.id ORDER BY m2.created_at DESC, m2.rowid DESC LIMIT 1) AS last_message
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id, c.title, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
            LIMIT ? OFFSET ?
            """,
            self.dialect,
        )

        def _execute(target_conn: Any) -> list[dict[str, Any]]:
            cursor = target_conn.execute(sql, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

        if conn is not None:
            return _execute(conn)
        with self.connection() as connection:
            return _execute(connection)

    def get_conversation(
        self,
        conversation_id: str,
        conn: Any | None = None,
    ) -> dict[str, Any] | None:
        sql = adapt_sql(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.id = ?
            GROUP BY c.id, c.title, c.created_at, c.updated_at
            """,
            self.dialect,
        )

        def _execute(target_conn: Any) -> dict[str, Any] | None:
            row = target_conn.execute(sql, (conversation_id,)).fetchone()
            return dict(row) if row else None

        if conn is not None:
            return _execute(conn)
        with self.connection() as connection:
            return _execute(connection)

    def update_conversation_title(
        self,
        conversation_id: str,
        title: str,
        conn: Any | None = None,
    ) -> dict[str, Any] | None:
        cleaned_title = title.strip()
        if not cleaned_title:
            raise ValueError("Conversation title cannot be empty")
        now = datetime.now(UTC).isoformat()
        sql = adapt_sql(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            self.dialect,
        )

        def _execute(target_conn: Any) -> dict[str, Any] | None:
            with target_conn:
                cursor = target_conn.execute(sql, (cleaned_title, now, conversation_id))
                if cursor.rowcount == 0:
                    return None
            return self.get_conversation(conversation_id, conn=target_conn)

        if conn is not None:
            return _execute(conn)
        with self.connection() as connection:
            return _execute(connection)

    def delete_conversation(
        self,
        conversation_id: str,
        conn: Any | None = None,
    ) -> bool:
        sql = adapt_sql("DELETE FROM conversations WHERE id = ?", self.dialect)

        def _execute(target_conn: Any) -> bool:
            with target_conn:
                cursor = target_conn.execute(sql, (conversation_id,))
                return cursor.rowcount > 0

        if conn is not None:
            return _execute(conn)
        with self.connection() as connection:
            return _execute(connection)

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[dict[str, Any]] | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
        message_id: str | None = None,
        created_at: str | None = None,
        conn: Any | None = None,
    ) -> dict[str, Any]:
        mid = message_id or str(uuid.uuid4())
        now = created_at or datetime.now(UTC).isoformat()
        citations_json = json.dumps(citations, ensure_ascii=False) if citations is not None else None
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else None

        insert_sql = adapt_sql(
            """
            INSERT INTO messages (id, conversation_id, role, content, citations, status, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self.dialect,
        )
        update_conv_sql = adapt_sql(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            self.dialect,
        )

        def _execute(target_conn: Any) -> dict[str, Any]:
            with target_conn:
                target_conn.execute(
                    insert_sql,
                    (mid, conversation_id, role, content, citations_json, status, metadata_json, now),
                )
                target_conn.execute(update_conv_sql, (now, conversation_id))
            return {
                "id": mid,
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "citations": citations or [],
                "status": status,
                "metadata": metadata or {},
                "created_at": now,
            }

        if conn is not None:
            return _execute(conn)
        with self.connection() as connection:
            return _execute(connection)

    def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int | None = None,
        offset: int | None = None,
        conn: Any | None = None,
    ) -> list[dict[str, Any]]:
        order_clause = "ORDER BY created_at ASC, rowid ASC" if self.dialect == "sqlite" else "ORDER BY created_at ASC"
        base_sql = f"""
            SELECT id, conversation_id, role, content, citations, status, metadata, created_at
            FROM messages
            WHERE conversation_id = ?
            {order_clause}
        """
        params: list[Any] = [conversation_id]
        if limit is not None and limit > 0:
            base_sql += " LIMIT ?"
            params.append(limit)
            if offset is not None and offset > 0:
                base_sql += " OFFSET ?"
                params.append(offset)

        sql = adapt_sql(base_sql, self.dialect)

        def _execute(target_conn: Any) -> list[dict[str, Any]]:
            cursor = target_conn.execute(sql, tuple(params))
            result: list[dict[str, Any]] = []
            for row in cursor.fetchall():
                item = dict(row)
                item["citations"] = json.loads(item["citations"]) if item.get("citations") else []
                item["metadata"] = json.loads(item["metadata"]) if item.get("metadata") else {}
                result.append(item)
            return result

        if conn is not None:
            return _execute(conn)
        with self.connection() as connection:
            return _execute(connection)

    def ensure_conversation(
        self,
        conversation_id: str | None = None,
        title: str | None = None,
        default_title: str | None = None,
        conn: Any | None = None,
    ) -> dict[str, Any]:
        final_title = title or default_title or "Cuộc trò chuyện mới"
        if conversation_id:
            existing = self.get_conversation(conversation_id, conn=conn)
            if existing:
                return existing
        return self.create_conversation(title=final_title, conversation_id=conversation_id, conn=conn)

    def conversation_exists(self, conversation_id: str, conn: Any | None = None) -> bool:
        return self.get_conversation(conversation_id, conn=conn) is not None

    def close(self) -> None:
        """Close anchor connections and release resources."""
        if self._anchor_conn is not None:
            try:
                self._anchor_conn.close()
            except Exception:
                pass
            self._anchor_conn = None


# ---------------------------------------------------------------------------
# Global Singleton & Dependency Injection Helpers
# ---------------------------------------------------------------------------

_default_manager: DatabaseManager | None = None


def get_db_manager(db_url: str | None = None) -> DatabaseManager:
    """Retrieve or create the global DatabaseManager singleton."""
    global _default_manager
    current_url = db_url or get_settings().database_url
    if _default_manager is None or (db_url is not None and _default_manager.db_url != current_url) or _default_manager.db_url != get_settings().database_url:
        if _default_manager is not None and _default_manager.db_url != current_url:
            _default_manager.close()
        _default_manager = DatabaseManager(current_url)
    return _default_manager


def reset_db_manager() -> None:
    """Reset the global DatabaseManager (primarily for test teardown)."""
    global _default_manager
    if _default_manager is not None:
        _default_manager.close()
        _default_manager = None


@contextmanager
def get_connection(db_url: str | None = None) -> Iterator[Any]:
    """Convenience context manager yielding an active database connection."""
    mgr = get_db_manager(db_url)
    with mgr.connection() as conn:
        yield conn


def init_db(db_url: str | None = None) -> None:
    """Initialize database tables and indexes."""
    get_db_manager(db_url).init_db()


# ---------------------------------------------------------------------------
# Module-level Repository Functions
# ---------------------------------------------------------------------------

def create_conversation(
    title: str | None = None,
    conversation_id: str | None = None,
    conn: Any | None = None,
) -> dict[str, Any]:
    return get_db_manager().create_conversation(title=title, conversation_id=conversation_id, conn=conn)


def list_conversations(
    limit: int = 50,
    offset: int = 0,
    conn: Any | None = None,
) -> list[dict[str, Any]]:
    return get_db_manager().list_conversations(limit=limit, offset=offset, conn=conn)


def get_conversation(
    conversation_id: str,
    conn: Any | None = None,
) -> dict[str, Any] | None:
    return get_db_manager().get_conversation(conversation_id=conversation_id, conn=conn)


def update_conversation_title(
    conversation_id: str,
    title: str,
    conn: Any | None = None,
) -> dict[str, Any] | None:
    return get_db_manager().update_conversation_title(conversation_id=conversation_id, title=title, conn=conn)


def delete_conversation(
    conversation_id: str,
    conn: Any | None = None,
) -> bool:
    return get_db_manager().delete_conversation(conversation_id=conversation_id, conn=conn)


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: list[dict[str, Any]] | None = None,
    status: str | None = None,
    metadata: dict[str, Any] | None = None,
    message_id: str | None = None,
    created_at: str | None = None,
    conn: Any | None = None,
) -> dict[str, Any]:
    return get_db_manager().add_message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        citations=citations,
        status=status,
        metadata=metadata,
        message_id=message_id,
        created_at=created_at,
        conn=conn,
    )


def get_conversation_messages(
    conversation_id: str,
    limit: int | None = None,
    offset: int | None = None,
    conn: Any | None = None,
) -> list[dict[str, Any]]:
    return get_db_manager().get_conversation_messages(
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
        conn=conn,
    )


def ensure_conversation(
    conversation_id: str | None = None,
    title: str | None = None,
    default_title: str | None = None,
    conn: Any | None = None,
) -> dict[str, Any]:
    return get_db_manager().ensure_conversation(
        conversation_id=conversation_id,
        title=title,
        default_title=default_title,
        conn=conn,
    )


def conversation_exists(conversation_id: str, conn: Any | None = None) -> bool:
    return get_db_manager().conversation_exists(conversation_id=conversation_id, conn=conn)
