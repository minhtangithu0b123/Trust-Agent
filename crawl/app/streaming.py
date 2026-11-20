"""Streaming and Server-Sent Events (SSE) support for Trust-AGENT.

Enables realtime token streaming to frontend clients with smooth typewriter effect,
followed by citation verification metadata and persistent SQLite session saving.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, AsyncIterator

from .db import add_message, ensure_conversation
from .router import run_router

logger = logging.getLogger(__name__)


def format_sse(event: str, data: Any) -> str:
    """Formats an SSE message frame according to the W3C spec."""
    if isinstance(data, (dict, list)):
        serialized = json.dumps(data, ensure_ascii=False)
    else:
        serialized = str(data)
    return f"event: {event}\ndata: {serialized}\n\n"


def split_text_into_tokens(text: str) -> list[str]:
    """Splits text into small natural word/token units for streaming."""
    if not text:
        return []
    # Tokenize preserving spaces and punctuation
    tokens = re.findall(r"\S+|\s+", text)
    return tokens


async def stream_router_sse(
    query: str,
    k: int = 5,
    conversation_id: str | None = None,
    delay_ms: float = 12.0,
) -> AsyncIterator[str]:
    """Asynchronous generator yielding Server-Sent Events for a router query."""
    try:
        # 1. Initialize persistent session
        conv = ensure_conversation(
            conversation_id=conversation_id,
            default_title=query[:255],
        )
        effective_conv_id = conv["id"]

        yield format_sse("status", {
            "step": "searching",
            "message": "Đang định tuyến và tra cứu điều luật...",
            "conversation_id": effective_conv_id,
        })

        # 2. Run router in worker thread to prevent event loop blocking
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: run_router(query, k, thread_id=effective_conv_id),
        )

        answer = response.get("answer", "")
        response["conversation_id"] = effective_conv_id
        response["thread_id"] = effective_conv_id
        response["session_id"] = effective_conv_id

        # 3. Stream text tokens with realistic typewriter pacing
        yield format_sse("status", {
            "step": "generating",
            "message": "Đang tổng hợp câu trả lời...",
            "conversation_id": effective_conv_id,
        })

        tokens = split_text_into_tokens(answer)
        for token in tokens:
            yield format_sse("token", {"delta": token})
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)

        # 4. Save to persistent SQLite database
        add_message(effective_conv_id, "user", query)
        add_message(
            effective_conv_id,
            "assistant",
            answer,
            citations=response.get("citations", []),
            status=response.get("status"),
            metadata={
                "domain": response.get("domain"),
                "guardrail_status": response.get("guardrail_status"),
            },
        )

        # 5. Emit final structured response with verified citations & guardrail status
        yield format_sse("final", response)
        yield format_sse("done", "[DONE]")

    except Exception as exc:
        logger.exception("Error during SSE streaming: %s", exc)
        yield format_sse("error", {"detail": str(exc)})
        yield format_sse("done", "[DONE]")
