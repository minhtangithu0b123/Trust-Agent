"""Privacy-preserving local evidence receipts and Merkle batch preparation."""

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import get_settings


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def receipt_db() -> Path:
    return get_settings().provenance_path


def create_receipt(answer: str, citations: list[dict[str, Any]], index_version: str) -> dict[str, Any]:
    receipt_id = str(uuid.uuid4())
    payload = {
        "receipt_id": receipt_id,
        "created_at": datetime.now(UTC).isoformat(),
        "index_version": index_version,
        "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        "evidence": [
            {
                "document_id": item.get("document_id"),
                "text_sha256": item.get("text_sha256"),
                "so_hieu": item.get("so_hieu"),
                "dieu": item.get("dieu"),
                "khoan": item.get("khoan"),
                "source": item.get("source"),
            }
            for item in citations
        ],
    }
    leaf_hash = hashlib.sha256(canonical_json(payload)).hexdigest()
    path = receipt_db()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS receipts (receipt_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL, leaf_hash TEXT NOT NULL, batch_root TEXT)")
        connection.execute(
            "INSERT INTO receipts (receipt_id, created_at, payload, leaf_hash) VALUES (?, ?, ?, ?)",
            (receipt_id, payload["created_at"], canonical_json(payload).decode("utf-8"), leaf_hash),
        )
    return {**payload, "leaf_hash": leaf_hash}


def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        raise ValueError("Cannot build an empty Merkle tree")
    level = [bytes.fromhex(item) for item in leaves]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def prepare_batch() -> dict[str, Any] | None:
    path = receipt_db()
    if not path.exists():
        return None
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT receipt_id, leaf_hash FROM receipts WHERE batch_root IS NULL ORDER BY created_at, receipt_id").fetchall()
        if not rows:
            return None
        root = merkle_root([row["leaf_hash"] for row in rows])
        connection.executemany("UPDATE receipts SET batch_root = ? WHERE receipt_id = ?", [(root, row["receipt_id"]) for row in rows])
    return {"root": root, "count": len(rows), "receipt_ids": [row["receipt_id"] for row in rows]}
