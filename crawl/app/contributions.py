"""Human-reviewed legal-data contributions with non-transferable points."""

import hashlib
import hmac
import sqlite3
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import AnyHttpUrl, BaseModel, Field

from .config import get_settings


class ContributionInput(BaseModel):
    kind: str = Field(pattern="^(new_source|correction)$")
    title: str = Field(min_length=4, max_length=180)
    source_url: AnyHttpUrl
    details: str = Field(min_length=20, max_length=6000)


def _connection() -> sqlite3.Connection:
    path = get_settings().provenance_path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS contributions (
        id TEXT PRIMARY KEY, content_hash TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
        title TEXT NOT NULL, source_url TEXT NOT NULL, details TEXT NOT NULL,
        status TEXT NOT NULL, points INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, reviewed_at TEXT
    )""")
    return connection


def submit_contribution(item: ContributionInput) -> dict[str, str]:
    contribution_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    source_url = str(item.source_url)
    digest = hashlib.sha256(f"{item.kind}\n{item.title}\n{source_url}\n{item.details}".encode()).hexdigest()
    try:
        with _connection() as db:
            db.execute(
                "INSERT INTO contributions (id, content_hash, kind, title, source_url, details, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
                (contribution_id, digest, item.kind, item.title, source_url, item.details, created_at),
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Contribution already submitted") from exc
    return {"id": contribution_id, "status": "pending_review"}


def list_contributions(token: str | None) -> list[dict]:
    expected = get_settings().reward_admin_token
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Reviewer authorization required")
    with _connection() as db:
        rows = db.execute("SELECT * FROM contributions ORDER BY created_at").fetchall()
    return [dict(row) for row in rows]


def review_contribution(contribution_id: str, approve: bool, token: str | None) -> dict:
    expected = get_settings().reward_admin_token
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Reviewer authorization required")
    reviewed_at = datetime.now(UTC).isoformat()
    points = 10 if approve else 0
    with _connection() as db:
        cursor = db.execute(
            "UPDATE contributions SET status = ?, points = ?, reviewed_at = ? WHERE id = ? AND status = 'pending'",
            ("approved" if approve else "rejected", points, reviewed_at, contribution_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pending contribution not found")
        row = db.execute("SELECT id, status, points, reviewed_at FROM contributions WHERE id = ?", (contribution_id,)).fetchone()
    return dict(row)
