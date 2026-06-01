# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""LiveDemoApp — AsgiApplication hosting a live HtmlBuilderHandler.

Mounts on an ``AsgiServer`` and exposes a single-page app at ``/`` plus
a set of ``@route()`` commands reachable both via HTTP and via WSX
(WebSocket eXtended). The page held by ``self.page`` survives across
calls; each command mutates it through the canonical builder API and
the route returns the freshly-rendered HTML in ``data.html``. The
browser updates the top panel from that value.

The route handlers are the **integration surface** of the demo: they
exercise ``HtmlBuilderHandler`` (lifecycle, render), ``genro_routes``
(dispatch via ``@route()``), ``genro_asgi`` (mount, HTTP and WSX
dispatch in one router) all together.

Replace ``DemoPage`` (or subclass ``LiveDemoApp`` overriding the
``page_class`` attribute) to drive the demo against a different
document.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from genro_asgi import AsgiApplication
from genro_routes import route

from .demo_page import DemoPage

_PACKAGE_DIR = Path(__file__).parent


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

    HTTP endpoints serve the SPA shell (``index.html``, ``app.js``).
    WSX endpoints (same methods, reached via WebSocket) mutate the
    page and return its current HTML.
    """

    openapi_info = {
        "title": "Genro Builders Live Demo",
        "version": "0.1.0",
        "description": "Interactive HTML builder over WebSocket.",
    }

    #: Override on a subclass to drive the demo against a different page.
    page_class: type[DemoPage] = DemoPage

    def __init__(self, **kwargs: Any) -> None:
        """Wire ``base_dir`` to the package directory by default.

        ``AsgiApplication`` reads ``base_dir`` to locate ``resources/``
        (where ``index.html`` and ``app.js`` live). Defaulting it to
        the package directory makes the demo work out of the box: the
        caller does not need to know where the resources are stored.
        """
        kwargs.setdefault("base_dir", _PACKAGE_DIR)
        super().__init__(**kwargs)

    def on_init(self, **kwargs: Any) -> None:
        """Build the initial page and seed its data.

        Called by ``AsgiApplication.__init__``. The page is created
        once and lives for the whole server lifetime.
        """
        self.page = self.page_class()
        self.page.create()
        self.page.data.set_item("page.title", "Hello")
        self.page.data.set_item("page.message", "Modifica i dati dalla REPL.")

    # ------------------------------------------------------------------
    # Static SPA shell — served via HTTP only (no payload via WSX)
    # ------------------------------------------------------------------

    @route(meta_mime_type="text/html")
    def index(self) -> str:
        """Return the SPA shell HTML."""
        return self._load_text("index.html")

    @route(meta_mime_type="application/javascript")
    def app_js(self) -> str:
        """Return the SPA client JavaScript."""
        return self._load_text("app.js")

    # ------------------------------------------------------------------
    # Commands — reachable via WSX (and via HTTP for poking with curl)
    # ------------------------------------------------------------------

    @route()
    def render(self) -> dict[str, Any]:
        """Return the current rendered HTML and a snapshot of both trees."""
        return self._respond()

    @route()
    def set_data(self, path: str, value: Any) -> dict[str, Any]:
        """Set a value into ``page.data`` and re-render."""
        self.page.data.set_item(path, value)
        return self._respond(ok=True)

    @route()
    def get_data(self, path: str) -> dict[str, Any]:
        """Read a value from ``page.data``."""
        return {"value": self.page.data.get_item(path)}

    @route()
    def keys(self, path: str = "") -> dict[str, Any]:
        """List keys of ``page.data`` at ``path`` (root if empty)."""
        bag = self.page.data.get_item(path) if path else self.page.data
        return {"keys": list(bag.keys()) if hasattr(bag, "keys") else []}

    @route()
    def set_attr(self, node_id: str, attr: str, value: Any) -> dict[str, Any]:
        """Set one attribute on the node identified by ``node_id``."""
        node = self.page.node_by_id(node_id)
        node.set_attr({attr: value})
        return self._respond(ok=True)

    @route()
    def set_value(self, node_id: str, value: Any) -> dict[str, Any]:
        """Replace ``node.value`` on the node identified by ``node_id``."""
        node = self.page.node_by_id(node_id)
        node.set_value(value)
        return self._respond(ok=True)

    @route()
    def add_child(
        self,
        parent_id: str,
        tag: str,
        text: Any = None,
        **attrs: Any,
    ) -> dict[str, Any]:
        """Append a new ``<tag>`` child under ``parent_id``.

        ``text`` becomes the node's value when present. Any other kwarg
        is forwarded to the grammar element as an attribute.
        """
        parent = self.page.node_by_id(parent_id)
        method = getattr(parent, tag)
        if text is not None:
            method(text, **attrs)
        else:
            method(**attrs)
        return self._respond(ok=True)

    @route()
    def remove_child(self, parent_id: str, label: str) -> dict[str, Any]:
        """Remove the child identified by ``label`` under ``parent_id``."""
        parent_bag = self.page.node_by_id(parent_id).value
        parent_bag.pop_node(label)
        return self._respond(ok=True)

    @route()
    def tree_source(self) -> dict[str, Any]:
        """Return only the source tree snapshot (no HTML, no data tree)."""
        return {"source": self._source_tree()}

    @route()
    def tree_data(self) -> dict[str, Any]:
        """Return only the data tree snapshot (no HTML, no source tree)."""
        return {"data": self._data_tree()}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _respond(self, ok: bool | None = None) -> dict[str, Any]:
        """Build a standard response: html + source tree + data tree.

        Used by every mutator route and by ``render`` so that the
        browser can update all three panels from a single message.
        """
        payload: dict[str, Any] = {
            "html": self.page.render(),
            "source": self._source_tree(),
            "data": self._data_tree(),
        }
        if ok is not None:
            payload["ok"] = ok
        return payload

    def _source_tree(self) -> dict[str, Any]:
        """Build a JSON-safe snapshot of the source bag.

        Top-level shape::

            {"kind": "root", "children": [node, node, ...]}

        Each node has::

            {
                "label": <bag label, e.g. "h1_0">,
                "tag":   <node_tag or label>,
                "attrs": { ... user attributes ... },
                "value": {
                    "kind": "literal"|"pointer"|"bag"|"none",
                    "raw":  <text>  # only when kind != "bag"
                    "pointer_kind": "caret"|"equals"  # only when kind == "pointer"
                },
                "children": [ ... only when value.kind == "bag" ... ]
            }
        """
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
        # A BuilderSource/Bag value means children — recurse.
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
        """Build a JSON-safe snapshot of the data bag.

        Top-level shape::

            {"kind": "root", "children": [entry, entry, ...]}

        Each entry has::

            {
                "key":   <bag key>,
                "kind":  "bag" | "scalar",
                "value": <repr>           # only when kind == "scalar"
                "children": [ ... ]       # only when kind == "bag"
            }
        """
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

    Primitive types pass through. Anything else is stringified so the
    response can be serialised even when a node holds an opaque Python
    object.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return repr(value)


if __name__ == "__main__":
    app = LiveDemoApp()
    print(f"page rendered:\n{app.page.render()}")
