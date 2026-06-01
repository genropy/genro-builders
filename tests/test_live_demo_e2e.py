# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""End-to-end tests for the live demo across the WSX boundary.

These tests cover the layers the unit suite in ``test_live_demo.py``
deliberately bypasses: ``@route()`` registration via ``genro_routes``,
WSX message parsing in ``MsgRequest``, and dispatch by
``WsxHandler.dispatch_message``. The route handlers themselves and
the underlying ``HtmlBuilderHandler`` are exercised end-to-end through
this stack.

The transport (``WebSocket``) is the only mocked layer: messages are
fed in as a Python list, responses are collected from a fake
``send_text``. Everything else — server, router, request registry,
dispatcher — is the real one.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("genro_asgi")
pytest.importorskip("genro_routes")

from genro_asgi import AsgiServer
from genro_asgi.wsx.protocol import build_wsx_message, parse_wsx_message

from genro_builders.contrib.live import LiveDemoApp

MOUNT = "live"


class FakeWebSocket:
    """Replays a queue of inbound WSX text messages and records outbound ones.

    Adapted from ``genro-asgi/tests/test_wsx_handler.py``.
    """

    def __init__(self, messages: list[str]) -> None:
        self._messages = list(messages)
        self.sent: list[str] = []
        self.accepted = False
        self._receive = AsyncMock()
        self._send = AsyncMock()

    async def accept(
        self, subprotocol: str | None = None, headers: Any = None,
    ) -> None:
        self.accepted = True

    async def send_text(self, data: str) -> None:
        self.sent.append(data)

    async def close(self, code: int = 1000, reason: str = "") -> None:  # noqa: ARG002
        pass

    async def iter_text(self):  # noqa: ANN201
        for msg in self._messages:
            yield msg


def _scope() -> dict[str, Any]:
    """Minimal ASGI WebSocket scope addressing the mounted prefix."""
    return {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "ws",
        "path": f"/{MOUNT}/",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 9000),
    }


@pytest.fixture
def server() -> AsgiServer:
    """A real ``AsgiServer`` with ``LiveDemoApp`` mounted as ``live``.

    Each test gets a fresh app, so command order across tests does not
    matter.
    """
    srv = AsgiServer(host="localhost", port=0)
    srv.mount(MOUNT, LiveDemoApp())
    return srv


async def _send(server: AsgiServer, messages: list[str]) -> list[dict[str, Any]]:
    """Feed ``messages`` through the server's WsxHandler and return parsed responses."""
    ws = FakeWebSocket(messages)
    with patch("genro_asgi.wsx.handler.WebSocket", return_value=ws):
        await server.wsx_handler(_scope(), AsyncMock(), AsyncMock())
    return [parse_wsx_message(s) for s in ws.sent]


def _path(cmd: str) -> str:
    return f"/{MOUNT}/{cmd}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_returns_initial_html(server: AsgiServer) -> None:
    """``render`` over WSX returns the initial seeded HTML."""
    msg = build_wsx_message(id="r1", method="POST", path=_path("render"))
    responses = await _send(server, [msg])
    assert len(responses) == 1
    resp = responses[0]
    assert resp["id"] == "r1"
    assert resp["status"] == 200
    assert "Hello" in resp["data"]["html"]


@pytest.mark.asyncio
async def test_set_data_then_render_reflects_change(server: AsgiServer) -> None:
    """A ``set_data`` followed by a ``render`` shows the new value."""
    set_msg = build_wsx_message(
        id="s1", method="POST", path=_path("set_data"),
        query={"path": "page.title", "value": "Live!"},
    )
    render_msg = build_wsx_message(id="r1", method="POST", path=_path("render"))
    responses = await _send(server, [set_msg, render_msg])
    by_id = {r["id"]: r for r in responses}
    assert by_id["s1"]["status"] == 200
    assert by_id["s1"]["data"]["ok"] is True
    assert "Live!" in by_id["s1"]["data"]["html"]
    assert "Live!" in by_id["r1"]["data"]["html"]


@pytest.mark.asyncio
async def test_add_child_via_wsx(server: AsgiServer) -> None:
    """``add_child`` over WSX appends a node visible in the next render."""
    msg = build_wsx_message(
        id="a1", method="POST", path=_path("add_child"),
        query={"parent_id": "body", "tag": "p", "text": "WSX!"},
    )
    responses = await _send(server, [msg])
    assert responses[0]["status"] == 200
    assert "WSX!" in responses[0]["data"]["html"]


@pytest.mark.asyncio
async def test_unknown_command_returns_error(server: AsgiServer) -> None:
    """An unknown route path produces an error response (not a crash)."""
    msg = build_wsx_message(id="x1", method="POST", path=_path("no_such_command"))
    responses = await _send(server, [msg])
    assert len(responses) == 1
    # Status may be a numeric code or a string error label (see
    # WsxHandler ROUTER_ERRORS). Either way, the framework returns a
    # well-formed envelope: id matches and there is a data dict.
    assert responses[0]["id"] == "x1"
    assert responses[0]["status"] != 200
