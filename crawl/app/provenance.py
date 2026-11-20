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
        _ensure_batches(connection)
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


def merkle_proof(leaves: list[str], leaf_index: int) -> list[dict[str, str]]:
    if not 0 <= leaf_index < len(leaves):
        raise IndexError("Leaf index is outside the batch")
    proof: list[dict[str, str]] = []
    level = [bytes.fromhex(item) for item in leaves]
    index = leaf_index
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sibling_index = index - 1 if index % 2 else index + 1
        proof.append({"hash": level[sibling_index].hex(), "position": "left" if sibling_index < index else "right"})
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
        index //= 2
    return proof


def verify_merkle_proof(leaf_hash: str, proof: list[dict[str, str]], expected_root: str) -> bool:
    current = bytes.fromhex(leaf_hash)
    for item in proof:
        sibling = bytes.fromhex(item["hash"])
        current = hashlib.sha256(sibling + current if item["position"] == "left" else current + sibling).digest()
    return current.hex() == expected_root


def _ensure_batches(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS batches (root TEXT PRIMARY KEY, count INTEGER NOT NULL, status TEXT NOT NULL, tx_hash TEXT, chain_id INTEGER, created_at TEXT NOT NULL)")


def prepare_batch() -> dict[str, Any] | None:
    path = receipt_db()
    if not path.exists():
        return None
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_batches(connection)
        rows = connection.execute("SELECT receipt_id, leaf_hash FROM receipts WHERE batch_root IS NULL ORDER BY created_at, receipt_id").fetchall()
        if not rows:
            return None
        root = merkle_root([row["leaf_hash"] for row in rows])
        connection.executemany("UPDATE receipts SET batch_root = ? WHERE receipt_id = ?", [(root, row["receipt_id"]) for row in rows])
        connection.execute("INSERT INTO batches (root, count, status, created_at) VALUES (?, ?, 'staged', ?)", (root, len(rows), datetime.now(UTC).isoformat()))
    return {"root": root, "count": len(rows), "receipt_ids": [row["receipt_id"] for row in rows]}


def next_batch() -> dict[str, Any] | None:
    path = receipt_db()
    if not path.exists():
        return None
    with sqlite3.connect(path) as connection:
        _ensure_batches(connection)
        row = connection.execute("SELECT root, count FROM batches WHERE status = 'staged' ORDER BY created_at LIMIT 1").fetchone()
    return {"root": row[0], "count": row[1]} if row else None


def mark_batch_anchored(root: str, tx_hash: str, chain_id: int) -> None:
    with sqlite3.connect(receipt_db()) as connection:
        _ensure_batches(connection)
        cursor = connection.execute("UPDATE batches SET status = 'anchored', tx_hash = ?, chain_id = ? WHERE root = ? AND status = 'staged'", (tx_hash, chain_id, root))
        if cursor.rowcount != 1:
            raise ValueError("Batch is not staged or was already anchored")
