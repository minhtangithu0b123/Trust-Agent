"""SQLite Persistent Checkpoint Saver for LangGraph.

Saves checkpoints, writes, and channel blobs into SQLite tables (WAL mode),
ensuring multi-turn conversational agent memory survives backend process restarts.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Sequence

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
)

from .config import get_settings
from .db import parse_sqlite_path

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT NOT NULL,
    checkpoint BLOB NOT NULL,
    metadata_type TEXT NOT NULL,
    metadata BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE IF NOT EXISTS langgraph_checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT NOT NULL,
    value BLOB NOT NULL,
    task_path TEXT DEFAULT '',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

CREATE TABLE IF NOT EXISTS langgraph_checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BLOB NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_lookup
ON langgraph_checkpoints(thread_id, checkpoint_ns, checkpoint_id DESC);
"""


class SqliteCheckpointSaver(BaseCheckpointSaver[str]):
    """Persistent LangGraph checkpointer backed by SQLite with WAL mode."""

    def __init__(self, db_path: str | Path | None = None, serde: Any = None) -> None:
        super().__init__(serde=serde)
        if db_path is None:
            settings = get_settings()
            db_path = parse_sqlite_path(settings.database_url)
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._all_conns: list[sqlite3.Connection] = []
        self._conn_lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
            )
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=10000;")
            self._local.conn = conn
            with self._conn_lock:
                self._all_conns.append(conn)
        return self._local.conn

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_db(self) -> None:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()
        finally:
            conn.close()

    def _load_blobs(
        self, thread_id: str, checkpoint_ns: str, versions: ChannelVersions
    ) -> dict[str, Any]:
        channel_values: dict[str, Any] = {}
        with self._cursor() as cursor:
            for channel, version in versions.items():
                cursor.execute(
                    """
                    SELECT type, blob FROM langgraph_checkpoint_blobs
                    WHERE thread_id = ? AND checkpoint_ns = ? AND channel = ? AND version = ?
                    """,
                    (thread_id, checkpoint_ns, channel, str(version)),
                )
                row = cursor.fetchone()
                if row:
                    blob_type, blob_bytes = row
                    if blob_type != "empty":
                        channel_values[channel] = self.serde.loads_typed((blob_type, blob_bytes))
        return channel_values

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)

        with self._cursor() as cursor:
            if checkpoint_id:
                cursor.execute(
                    """
                    SELECT checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata_type, metadata
                    FROM langgraph_checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                    """,
                    (thread_id, checkpoint_ns, checkpoint_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata_type, metadata
                    FROM langgraph_checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ?
                    ORDER BY checkpoint_id DESC
                    LIMIT 1
                    """,
                    (thread_id, checkpoint_ns),
                )
            row = cursor.fetchone()
            if not row:
                return None

            (
                cid,
                parent_cid,
                cp_type,
                cp_bytes,
                meta_type,
                meta_bytes,
            ) = row

            cursor.execute(
                """
                SELECT task_id, channel, type, value
                FROM langgraph_checkpoint_writes
                WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                ORDER BY idx ASC
                """,
                (thread_id, checkpoint_ns, cid),
            )
            write_rows = cursor.fetchall()
            pending_writes = [
                (task_id, channel, self.serde.loads_typed((w_type, w_val)))
                for task_id, channel, w_type, w_val in write_rows
            ]

        checkpoint_: Checkpoint = self.serde.loads_typed((cp_type, cp_bytes))
        metadata_ = self.serde.loads_typed((meta_type, meta_bytes))

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": cid,
                }
            },
            checkpoint={
                **checkpoint_,
                "channel_values": self._load_blobs(
                    thread_id, checkpoint_ns, checkpoint_["channel_versions"]
                ),
            },
            metadata=metadata_,
            pending_writes=pending_writes,
            parent_config=(
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_cid,
                    }
                }
                if parent_cid
                else None
            ),
        )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        cp_type, cp_bytes = self.serde.dumps_typed(
            {k: v for k, v in checkpoint.items() if k != "channel_values"}
        )
        meta_type, meta_bytes = self.serde.dumps_typed(metadata)

        with self._cursor() as cursor:
            # 1. Save Blobs
            for channel, version in new_versions.items():
                if channel in checkpoint["channel_values"]:
                    b_type, b_bytes = self.serde.dumps_typed(checkpoint["channel_values"][channel])
                else:
                    b_type, b_bytes = "empty", b""
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO langgraph_checkpoint_blobs
                    (thread_id, checkpoint_ns, channel, version, type, blob)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (thread_id, checkpoint_ns, channel, str(version), b_type, b_bytes),
                )

            # 2. Save Checkpoint
            cursor.execute(
                """
                INSERT OR REPLACE INTO langgraph_checkpoints
                (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    checkpoint_ns,
                    checkpoint_id,
                    parent_checkpoint_id,
                    cp_type,
                    cp_bytes,
                    meta_type,
                    meta_bytes,
                ),
            )

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        with self._cursor() as cursor:
            for idx, (channel, val) in enumerate(writes):
                write_idx = WRITES_IDX_MAP.get(channel, idx)
                val_type, val_bytes = self.serde.dumps_typed(val)
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO langgraph_checkpoint_writes
                    (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, type, value, task_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        thread_id,
                        checkpoint_ns,
                        checkpoint_id,
                        task_id,
                        write_idx,
                        channel,
                        val_type,
                        val_bytes,
                        task_path,
                    ),
                )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"] if config else None
        checkpoint_ns = config["configurable"].get("checkpoint_ns") if config else None
        checkpoint_id = get_checkpoint_id(config) if config else None
        before_checkpoint_id = get_checkpoint_id(before) if before else None

        query = """
            SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata_type, metadata
            FROM langgraph_checkpoints
            WHERE 1=1
        """
        params: list[Any] = []
        if thread_id is not None:
            query += " AND thread_id = ?"
            params.append(thread_id)
        if checkpoint_ns is not None:
            query += " AND checkpoint_ns = ?"
            params.append(checkpoint_ns)
        if checkpoint_id is not None:
            query += " AND checkpoint_id = ?"
            params.append(checkpoint_id)
        if before_checkpoint_id is not None:
            query += " AND checkpoint_id < ?"
            params.append(before_checkpoint_id)

        query += " ORDER BY checkpoint_id DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"

        with self._cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        for (
            t_id,
            ns,
            cid,
            parent_cid,
            cp_type,
            cp_bytes,
            meta_type,
            meta_bytes,
        ) in rows:
            metadata = self.serde.loads_typed((meta_type, meta_bytes))
            if filter and not all(
                metadata.get(query_key) == query_val
                for query_key, query_val in filter.items()
            ):
                continue

            checkpoint_: Checkpoint = self.serde.loads_typed((cp_type, cp_bytes))
            with self._cursor() as cursor:
                cursor.execute(
                    """
                    SELECT task_id, channel, type, value
                    FROM langgraph_checkpoint_writes
                    WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                    ORDER BY idx ASC
                    """,
                    (t_id, ns, cid),
                )
                write_rows = cursor.fetchall()

            pending_writes = [
                (task_id, channel, self.serde.loads_typed((w_type, w_val)))
                for task_id, channel, w_type, w_val in write_rows
            ]

            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": t_id,
                        "checkpoint_ns": ns,
                        "checkpoint_id": cid,
                    }
                },
                checkpoint={
                    **checkpoint_,
                    "channel_values": self._load_blobs(
                        t_id, ns, checkpoint_["channel_versions"]
                    ),
                },
                metadata=metadata,
                parent_config=(
                    {
                        "configurable": {
                            "thread_id": t_id,
                            "checkpoint_ns": ns,
                            "checkpoint_id": parent_cid,
                        }
                    }
                    if parent_cid
                    else None
                ),
                pending_writes=pending_writes,
            )

    def delete_thread(self, thread_id: str) -> None:
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM langgraph_checkpoints WHERE thread_id = ?", (thread_id,))
            cursor.execute("DELETE FROM langgraph_checkpoint_writes WHERE thread_id = ?", (thread_id,))
            cursor.execute("DELETE FROM langgraph_checkpoint_blobs WHERE thread_id = ?", (thread_id,))

    def delete_all_threads(self) -> None:
        """Clear all persisted LangGraph conversation memory."""
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM langgraph_checkpoints")
            cursor.execute("DELETE FROM langgraph_checkpoint_writes")
            cursor.execute("DELETE FROM langgraph_checkpoint_blobs")

    def close(self) -> None:
        """Closes all connections opened by any thread."""
        with self._conn_lock:
            for conn in self._all_conns:
                try:
                    conn.close()
                except Exception:
                    pass
            self._all_conns.clear()
        if hasattr(self._local, "conn"):
            self._local.conn = None

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self.get_tuple(config)

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        return self.put_writes(config, writes, task_id, task_path)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    async def adelete_thread(self, thread_id: str) -> None:
        return self.delete_thread(thread_id)


_GLOBAL_CHECKPOINTER: SqliteCheckpointSaver | None = None
_LOCK = threading.Lock()


def get_sqlite_checkpointer(db_path: str | Path | None = None) -> SqliteCheckpointSaver:
    """Returns singleton instance of SqliteCheckpointSaver."""
    global _GLOBAL_CHECKPOINTER
    if _GLOBAL_CHECKPOINTER is None or db_path is not None:
        with _LOCK:
            if _GLOBAL_CHECKPOINTER is None or db_path is not None:
                _GLOBAL_CHECKPOINTER = SqliteCheckpointSaver(db_path=db_path)
    return _GLOBAL_CHECKPOINTER
