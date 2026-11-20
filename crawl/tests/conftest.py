"""Pytest configuration and offline environment fixtures for Trust-AGENT.

Guarantees:
1. 100% offline execution without network or real OPENAI_API_KEY.
2. Intercepts and blocks any unexpected outbound HTTP request.
3. Fixes Windows sandbox asyncio self-pipe using kernel named pipes.
"""

from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

# Ensure crawl directory and local venv packages are on sys.path
CRAWL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CRAWL_DIR not in sys.path:
    sys.path.insert(0, CRAWL_DIR)

VENV_SITE_PACKAGES = os.path.abspath(os.path.join(CRAWL_DIR, ".venv", "Lib", "site-packages"))
if os.path.exists(VENV_SITE_PACKAGES) and VENV_SITE_PACKAGES not in sys.path:
    sys.path.append(VENV_SITE_PACKAGES)

# Disable external telemetry and tracing
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Ensure OPENAI_API_KEY has a placeholder if not set, preventing unconfigured crashes
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "mock-openai-api-key-for-offline-unit-tests"

# Windows sandbox offline self-pipe fix:
# In Windows network-isolated sandbox, localhost TCP connections for asyncio self-pipe
# are blocked with WinError 10013. We route asyncio's self-pipe through named pipes.
if sys.platform == "win32":
    import asyncio
    import asyncio.proactor_events
    import asyncio.windows_events
    import asyncio.windows_utils
    import signal
    import _overlapped
    import _winapi

    signal.set_wakeup_fd = lambda fd, *args, **kwargs: -1

    class PipeSocket:
        """Lightweight socket-like adapter wrapping an overlapped Windows named pipe."""

        def __init__(self, handle: int):
            self._handle = handle

        def fileno(self) -> int:
            return self._handle

        def setblocking(self, flag: bool) -> None:
            pass

        def send(self, data: bytes) -> int:
            ov = _overlapped.Overlapped(0)
            try:
                ov.WriteFile(self._handle, data)
                ov.getresult()
                return len(data)
            except OSError:
                return 0

        def close(self) -> None:
            if self._handle is not None:
                try:
                    _winapi.CloseHandle(self._handle)
                except OSError:
                    pass
                self._handle = None

    def _patched_make_self_pipe(self):
        h1, h2 = asyncio.windows_utils.pipe(overlapped=(True, True))
        self._ssock = PipeSocket(h1)
        self._csock = PipeSocket(h2)
        self._internal_fds += 1

    def _patched_close_self_pipe(self):
        if self._ssock:
            self._ssock.close()
            self._ssock = None
        if self._csock:
            self._csock.close()
            self._csock = None

    asyncio.proactor_events.BaseProactorEventLoop._make_self_pipe = _patched_make_self_pipe
    asyncio.proactor_events.BaseProactorEventLoop._close_self_pipe = _patched_close_self_pipe


@pytest.fixture(autouse=True)
def prevent_external_network_calls(monkeypatch):
    """Guard that intercepts outbound HTTP requests in tests to ensure 100% offline purity."""
    import socket

    orig_connect = socket.socket.connect
    orig_connect_ex = socket.socket.connect_ex
    orig_getaddrinfo = socket.getaddrinfo

    def _is_allowed(host: Any) -> bool:
        if not host:
            return True
        h = str(host).strip().lower()
        return h in ("127.0.0.1", "localhost", "::1", "testserver", "")

    def guarded_connect(self, address):
        host, port = address[0], address[1] if len(address) > 1 else None
        if not _is_allowed(host):
            raise RuntimeError(
                f"BLOCKED OUTBOUND NETWORK CALL in unit test to {host}:{port}. "
                "All external API calls (e.g. OpenAI) must be mocked for offline execution."
            )
        return orig_connect(self, address)

    def guarded_connect_ex(self, address):
        host, port = address[0], address[1] if len(address) > 1 else None
        if not _is_allowed(host):
            raise RuntimeError(
                f"BLOCKED OUTBOUND NETWORK CALL in unit test to {host}:{port}. "
                "All external API calls (e.g. OpenAI) must be mocked for offline execution."
            )
        return orig_connect_ex(self, address)

    def guarded_getaddrinfo(host, port, *args, **kwargs):
        if not _is_allowed(host):
            raise RuntimeError(
                f"BLOCKED OUTBOUND DNS/NETWORK CALL in unit test to {host}:{port}. "
                "All external API calls (e.g. OpenAI) must be mocked for offline execution."
            )
        return orig_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
