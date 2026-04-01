# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagRendererBase — abstract base class for Bag renderers.

A renderer transforms a built Bag into a serialized output (string, bytes).
It is a "dead" output: no live objects, no reactivity.

Decorators:
    @render_handler: Mark a method as render handler for a specific tag.
                     Used by _walk_render() for automatic tag dispatch.

Example:
    >>> class MarkdownRenderer(BagRendererBase):
    ...     @render_handler
    ...     def h1(self, node, ctx):
    ...         return f"# {ctx['node_value']}"
    ...
    ...     def render(self, built_bag):
    ...         parts = list(self._walk_render(built_bag))
    ...         return '\\n\\n'.join(p for p in parts if p)
"""
from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Iterator
from typing import Any

from genro_bag import Bag, BagNode

# =============================================================================
# Decorator
# =============================================================================


def render_handler(func: Callable) -> Callable:
    """Decorator to mark a method as render handler for a tag.

    The method name becomes the tag it handles.

    Example:
        @render_handler
        def h1(self, node, ctx):
            return f"# {ctx['node_value']}"
    """
    func._render_handler = True  # type: ignore[attr-defined]
    return func


# =============================================================================
# BagRendererBase
# =============================================================================


class BagRendererBase(ABC):
    """Abstract base class for Bag renderers (dead output).

    Provides:
        - @render_handler dispatch: tag-based rendering infrastructure
        - _walk_render(), _build_context(), default_render(): rendering utilities
        - render(): main entry point (subclass should override or use as-is)

    Subclasses define render handlers for specific tags and optionally
    override render() for custom output assembly.
    """

    _class_render_handlers: dict[str, Callable]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Collect @render_handler decorated methods into _class_render_handlers."""
        super().__init_subclass__(**kwargs)

        cls._class_render_handlers = {}

        for parent in cls.__mro__[1:]:
            if hasattr(parent, "_class_render_handlers"):
                cls._class_render_handlers.update(parent._class_render_handlers)
                break

        for name, obj in cls.__dict__.items():
            if callable(obj) and getattr(obj, "_render_handler", False):
                cls._class_render_handlers[name] = obj

    def __init__(self, builder: Any) -> None:
        """Initialize renderer with builder reference.

        Args:
            builder: The BagBuilderBase instance that owns this renderer.
        """
        self.builder = builder
        self._render_handlers = dict(type(self)._class_render_handlers)

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def render(self, built_bag: Bag) -> str:
        """Render the built Bag to output string.

        Default implementation walks the bag and joins parts with newlines.
        Override for custom assembly logic.

        Args:
            built_bag: The built Bag to render.

        Returns:
            Rendered output string.
        """
        parts = list(self._walk_render(built_bag))
        return "\n".join(p for p in parts if p)

    def _walk_render(self, bag: Bag) -> Iterator[str]:
        """Walk bag and render each node via handler dispatch."""
        for node in bag:
            result = self._render_node(node)
            if result is not None:
                yield result

    def _render_node(self, node: BagNode) -> str | None:
        """Render a single node.

        Resolution order:
        1. @render_handler method matching tag name
        2. default_render()
        """
        tag = node.node_tag or node.label
        ctx = self._build_context(node)

        handler = self._render_handlers.get(tag)
        if handler:
            return handler(self, node, ctx)

        return self.default_render(node, ctx)

    def _build_context(self, node: BagNode) -> dict[str, Any]:
        """Build context dict for render handlers.

        Context contains:
            - node_value: The node's value (string)
            - node_label: The node's label
            - _node: The full BagNode (for advanced access)
            - children: Rendered children (if node has Bag value)
            - All node attributes
        """
        node_value = node.get_value(static=True)

        ctx: dict[str, Any] = {
            "node_value": "" if node_value is None or isinstance(node_value, Bag) else str(node_value),
            "node_label": node.label,
            "_node": node,
        }

        ctx.update(node.attr)

        if isinstance(node_value, Bag):
            children_parts = list(self._walk_render(node_value))
            ctx["children"] = self.join_children(children_parts)
        else:
            ctx["children"] = ""

        return ctx

    def join_children(self, parts: list[str]) -> str:
        """Join rendered children. Override for different joining logic."""
        return "\n".join(p for p in parts if p)

    # -------------------------------------------------------------------------
    # Default render
    # -------------------------------------------------------------------------

    def default_render(self, node: BagNode, ctx: dict[str, Any]) -> str | None:
        """Default render: return value or children.

        Override in subclass for custom default behavior.
        """
        if ctx["node_value"]:
            return ctx["node_value"]
        if ctx["children"]:
            return ctx["children"]
        return None
