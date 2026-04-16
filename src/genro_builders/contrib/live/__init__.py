# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Live remote control for BuilderManager sessions.

Enable remote control on a running manager::

    from genro_builders.contrib.live import enable_remote

    class MyApp(ReactiveManager):
        def on_init(self):
            self.page = self.register_builder('page', HtmlBuilder)
            self.run(subscribe=True)

    app = MyApp()
    server = enable_remote(app, port=9999, name="myapp")

Connect from another process::

    from genro_builders.contrib.live import connect

    remote = connect(name="myapp")
    remote.source("page").div("Hello!")
    remote.data["page.title"] = "Updated"
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from genro_builders.contrib.live._proxy import DataProxy, LiveProxy, SourceProxy
from genro_builders.contrib.live._registry import LiveRegistry
from genro_builders.contrib.live._server import LiveServer, LiveSession

if TYPE_CHECKING:
    from genro_builders.manager import BuilderManager

__all__ = [
    "LiveSession",
    "LiveServer",
    "LiveProxy",
    "SourceProxy",
    "DataProxy",
    "LiveRegistry",
    "enable_remote",
    "connect",
]


def enable_remote(
    manager: BuilderManager,
    port: int = 0,
    name: str | None = None,
) -> LiveServer:
    """Enable remote control on a running BuilderManager.

    Creates a LiveSession, starts a LiveServer on the given port,
    and optionally registers the session by name in the LiveRegistry.

    Args:
        manager: The BuilderManager instance to expose remotely.
        port: Port to listen on (0 = auto-select free port).
        name: Optional registry name. If given, the session is registered
            so clients can connect by name instead of port+token.

    Returns:
        The started LiveServer instance. Access ``server.port`` and
        ``server.token`` for connection details.
    """
    session = LiveSession(manager)
    return session.serve(port=port, name=name)


def connect(
    name: str | None = None,
    host: str = "localhost",
    port: int | None = None,
    token: str = "",
) -> LiveProxy:
    """Connect to a remote live session.

    Either *name* (registry lookup) or *port* + *token* (direct) must
    be provided.

    Args:
        name: Registry name — looks up port and token from LiveRegistry.
        host: Hostname (default ``localhost``).
        port: Port number (required if name is not given).
        token: Auth token (required if name is not given).

    Returns:
        A LiveProxy connected to the remote session.

    Raises:
        ValueError: If neither name nor port is specified, or if
            the named session is not found in the registry.
    """
    if name is not None:
        registry = LiveRegistry()
        info = registry.get_info(name)
        if info is None:
            raise ValueError(f"Session '{name}' not found in registry")
        port = info["port"]
        token = info.get("token", "")
    elif port is None:
        raise ValueError("Either 'name' or 'port' must be specified")

    return LiveProxy(host=host, port=port, token=token)
