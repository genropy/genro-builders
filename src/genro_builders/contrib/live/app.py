# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""LiveDemoApp — AsgiApplication hosting several live demo pages.

Mounts on an ``AsgiServer`` and exposes a single-page app at ``/`` plus a
Python REPL over WSX. Several demo pages (auto-discovered from ``pages/``)
are instantiated up front and kept alive in parallel; one is "current".
Selecting another demo only switches the pointer — each page keeps its own
state and its own persistent REPL namespace.

Each REPL snippet runs inside ``current_page.live()``, so every mutation
re-renders the current page to the default target ``resources/out.html``,
which the browser reloads in an ``<iframe>``.

The REPL is the integration surface of the demo: it exercises
``InteractiveDemo`` (an ``HtmlBuilderHandler`` with shortcuts),
``genro_routes`` (``@route()`` dispatch) and ``genro_asgi`` (mount, HTTP
and WSX) together.

The snippet namespace exposes a single name, ``page`` (the current demo).
From it you reach ``page.data``, ``page.set_data(...)``, ``page.node[id]``,
etc.

Security note: the REPL runs ``exec`` on code received over the socket.
The builtins are reduced for clarity, NOT as a sandbox — this is a local
developer tool. Do not expose it on a public interface.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from genro_asgi import AsgiApplication
from genro_routes import route

from genro_builders.builder import BuilderHandler

from . import pages
from .interactive_demo import InteractiveDemo

_PACKAGE_DIR = Path(__file__).parent
_OUT_HTML = _PACKAGE_DIR / "resources" / "out.html"
_OUT_XML = _PACKAGE_DIR / "resources" / "out.xml"

#: Builtins exposed to REPL snippets. Reduced for clarity (an honest,
#: guided surface), NOT a security boundary.
_REPL_BUILTINS = {
    name: __builtins__[name] if isinstance(__builtins__, dict)
    else getattr(__builtins__, name)
    for name in (
        "len", "range", "enumerate", "zip", "map", "filter", "sorted",
        "str", "int", "float", "bool", "list", "dict", "tuple", "set",
        "print", "repr", "abs", "min", "max", "sum", "any", "all",
    )
}


def _pointer_kind(text: str) -> str | None:
    """Return ``'caret'``/``'equals'`` if ``text`` is a pointer, else ``None``."""
    if not isinstance(text, str) or not text:
        return None
    head = text[0]
    if head == "^":
        return "caret"
    if head == "=":
        return "equals"
    return None


class LiveDemoApp(AsgiApplication):
    """Live HTML demo mounted as an ASGI application.

    HTTP endpoints serve the SPA shell (``index.html``, ``app.js``) and the
    rendered document (``out.html``). WSX endpoints switch the current demo
    (``select``), run snippets (``repl``) and return tree snapshots; the
    rendered HTML travels through ``out.html``.
    """

    openapi_info = {
        "title": "Genro Builders Live Demo",
        "version": "0.1.0",
        "description": "Interactive HTML builder REPL over WebSocket.",
    }

    def __init__(self, **kwargs: Any) -> None:
        """Wire ``base_dir`` to the package directory by default."""
        kwargs.setdefault("base_dir", _PACKAGE_DIR)
        super().__init__(**kwargs)

    def on_init(self, **kwargs: Any) -> None:
        """Discover the demo pages, mount them on one handler, render current.

        Every demo page is a builder mounted on a single ``BuilderHandler``
        (the app is its application, so the handler is reactive). Mounting
        creates each page (``setup`` + ``main`` + first calculation); the
        page's HTML render target is ``out.html``. ``self.demos`` maps key →
        builder, ``self.titles`` key → title, ``self.namespaces`` key →
        persistent REPL namespace. ``self.current`` is the selected key (the
        first by sort order). The initial render makes ``out.html`` exist
        before the browser's iframe loads it.
        """
        discovered = pages.discover()
        self.handler = BuilderHandler(application=self)
        self.demos: dict[str, InteractiveDemo] = {}
        self.titles: dict[str, str] = {}
        self.namespaces: dict[str, dict[str, Any]] = {}
        for key, (title, demo_class) in discovered.items():
            page = demo_class()
            page.set_render_target(str(_OUT_HTML), "html")
            self.demos[key] = page
            self.titles[key] = title
            self.namespaces[key] = {"__builtins__": _REPL_BUILTINS, "page": page}
        self.handler.add_builder(**self.demos)   # mount + create each page
        self.current: str = next(iter(self.demos))
        self._render_current()

    def _render_current(self) -> None:
        """Refresh both views of the current demo (html render + raw xml)."""
        self.page.render()
        self._write_raw_xml()

    def _write_raw_xml(self) -> None:
        """Write ``out.xml``: the raw structural view of the source —
        markers and unresolved pointers shown verbatim.

        This is ``Bag.to_xml`` on the source directly, NOT
        ``render(mode="xml")`` (which is a real render: pointers
        resolved, markers filtered). Called after every source mutation
        so the raw view tracks the document — ``live()`` only re-renders
        ``out.html``, it does not know about this debug view.
        """
        raw_xml = self.page.source.to_xml(pretty=True)
        _OUT_XML.write_text(raw_xml or "", encoding="utf-8")

    @property
    def page(self) -> InteractiveDemo:
        """The current demo handler."""
        return self.demos[self.current]

    # ------------------------------------------------------------------
    # Static SPA shell + rendered document — served via HTTP
    # ------------------------------------------------------------------

    @route(meta_mime_type="text/html")
    def index(self) -> str:
        """Return the SPA shell HTML."""
        return self._load_text("index.html")

    @route(meta_mime_type="application/javascript")
    def app_js(self) -> str:
        """Return the SPA client JavaScript."""
        return self._load_text("app.js")

    @route(meta_mime_type="text/css")
    def demo_css(self) -> str:
        """Return the shared demo stylesheet (linked by every demo body)."""
        return self._load_text("demo.css")

    @route(meta_mime_type="text/html")
    def out(self, **_ignored: Any) -> str:
        """Return the current rendered document (the live target file).

        Accepts and ignores extra query params (the browser appends a
        ``?t=<timestamp>`` cache-buster when reloading the iframe).
        """
        return self._load_text("out.html")

    @route(meta_mime_type="text/plain")
    def out_xml(self, **_ignored: Any) -> str:
        """Return the current document as raw XML (the live xml target)."""
        return self._load_text("out.xml")

    # ------------------------------------------------------------------
    # Demo selection + REPL — reachable via WSX
    # ------------------------------------------------------------------

    @route()
    def menu(self) -> dict[str, Any]:
        """Return the demo menu and the current selection."""
        return {
            "demos": [{"key": k, "title": self.titles[k]} for k in self.demos],
            "current": self.current,
        }

    @route()
    def select(self, key: str) -> dict[str, Any]:
        """Switch the current demo to ``key`` and re-render it to out.html."""
        if key not in self.demos:
            return {"ok": False, "error": f"unknown demo: {key}"}
        self.current = key
        self._render_current()
        return {
            "ok": True,
            "current": key,
            "source": self._source_tree(),
            "data": self._data_tree(),
        }

    @route()
    def repl(self, source: str) -> dict[str, Any]:
        """Run a Python ``source`` snippet against the current demo.

        The snippet runs inside ``handler.live()``, so every mutation
        re-renders the touched page to ``out.html``. Uses the current demo's
        persistent namespace (variables survive across runs, per demo).
        Returns the source/data tree snapshots; the HTML is picked up by the
        browser reloading ``out.html``. On error returns the exception text.
        """
        try:
            with self.handler.live():
                exec(source, self.namespaces[self.current])
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        self._write_raw_xml()
        return {
            "ok": True,
            "source": self._source_tree(),
            "data": self._data_tree(),
        }

    @route()
    def set_value(self, path: str, value: Any) -> dict[str, Any]:
        """Write ``value`` into the current demo's data at ``path``.

        The write-back endpoint for two-way binding: the browser sends the
        absolute path (read from a ``data-<name>-pointer`` attribute) and
        the edited value when an input changes. Runs inside ``handler.live()``
        so the document re-renders. ``path`` is absolute, as resolved at
        render time — no relative composition here.
        """
        with self.handler.live():
            self.page.data.set_item(path, value)
        self._write_raw_xml()
        return {
            "ok": True,
            "source": self._source_tree(),
            "data": self._data_tree(),
        }

    @route()
    def source_code(self) -> dict[str, Any]:
        """Return the Python source of the current demo's module."""
        module = inspect.getmodule(type(self.page))
        return {"source_code": inspect.getsource(module)}

    @route()
    def tree_source(self) -> dict[str, Any]:
        """Return only the current demo's source tree snapshot."""
        return {"source": self._source_tree()}

    @route()
    def tree_data(self) -> dict[str, Any]:
        """Return only the current demo's data tree snapshot."""
        return {"data": self._data_tree()}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _source_tree(self) -> dict[str, Any]:
        """Build a JSON-safe snapshot of the current demo's source bag."""
        roots: list[dict[str, Any]] = []
        for node in self.page.source:
            roots.append(self._serialize_source_node(node))
        return {"kind": "root", "children": roots}

    def _serialize_source_node(self, node: Any) -> dict[str, Any]:
        attrs = {k: _scalar(v) for k, v in dict(node.attr or {}).items()}
        value = node.value
        node_info: dict[str, Any] = {
            "label": node.label,
            "tag": node.node_tag or node.label,
            "attrs": attrs,
        }
        if value is None:
            node_info["value"] = {"kind": "none"}
            return node_info
        # A SourceBag/Bag value means children — recurse.
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
            children = [self._serialize_source_node(child) for child in value]
            node_info["value"] = {"kind": "bag"}
            node_info["children"] = children
            return node_info
        if isinstance(value, str):
            pk = _pointer_kind(value)
            if pk is not None:
                node_info["value"] = {
                    "kind": "pointer",
                    "raw": value,
                    "pointer_kind": pk,
                }
            else:
                node_info["value"] = {"kind": "literal", "raw": value}
            return node_info
        node_info["value"] = {"kind": "literal", "raw": _scalar(value)}
        return node_info

    def _data_tree(self) -> dict[str, Any]:
        """Build a JSON-safe snapshot of the current demo's data bag."""
        return {"kind": "root", "children": self._serialize_bag(self.page.data)}

    def _serialize_bag(self, bag: Any) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for key in bag.keys():
            value = bag.get_item(key) if hasattr(bag, "get_item") else None
            if hasattr(value, "keys") and not isinstance(value, (str, bytes)):
                entries.append({
                    "key": key,
                    "kind": "bag",
                    "children": self._serialize_bag(value),
                })
            else:
                entries.append({
                    "key": key,
                    "kind": "scalar",
                    "value": _scalar(value),
                })
        return entries

    def _load_text(self, name: str) -> str:
        """Read a static resource as text via ``load_resource``."""
        result = self.load_resource(name=name)
        if result is None:
            raise FileNotFoundError(f"resource not found: {name}")
        content, _mime = result
        return content.decode("utf-8")


def _scalar(value: Any) -> Any:
    """Return a JSON-safe representation of ``value``.

    Primitive types pass through. Anything else is stringified.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return repr(value)


if __name__ == "__main__":
    app = LiveDemoApp()
    print(f"current demo: {app.current}\n{app.page.render()}")
