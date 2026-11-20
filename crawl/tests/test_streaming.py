"""Unit tests for Server-Sent Events (SSE) streaming."""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.streaming import format_sse, split_text_into_tokens


def test_split_text_into_tokens():
    text = "Anh A đã vi phạm vượt đèn đỏ."
    tokens = split_text_into_tokens(text)
    assert len(tokens) >= 5
    assert "".join(tokens) == text


def test_format_sse():
    msg = format_sse("token", {"delta": "Xin chào"})
    assert msg.startswith("event: token\n")
    assert 'data: {"delta": "Xin chào"}\n\n' in msg


def test_router_ask_stream_endpoint():
    client = TestClient(app)
    response = client.post(
        "/router/ask/stream",
        json={"query": "chào bạn", "k": 3},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = [line for line in response.text.split("\n") if line.startswith("event:")]
    assert "event: status" in events
    assert "event: token" in events
    assert "event: final" in events
    assert "event: done" in events


def test_router_ask_stream_flag():
    client = TestClient(app)
    response = client.post(
        "/router/ask",
        json={"query": "chào bạn", "k": 3, "stream": True},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
