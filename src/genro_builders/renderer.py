# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagRendererBase — abstract base class for Bag renderers.

A renderer transforms a built Bag into a serialized output (string, bytes).
It is a "dead" output: no live objects, no reactivity.

Pointer formali and just-in-time resolution:
    The built Bag retains ``^pointer`` strings verbatim (pointer formali).
    During ``_walk_render()``, each node is resolved just-in-time via
    ``builder._resolve_node(node, data)`` which returns a dict with
    ``node_value``, ``attrs``, and ``node``. The renderer works with
    resolved values without modifying the built Bag.

Decorators:
    @renderer: Mark a method as render handler for a specific tag.
               If body is empty (...), uses default_render with kwargs.
               If body has logic, the method IS the handler.

Example:
    >>> class MarkdownRenderer(BagRendererBase):
    ...     @renderer(template="# {node_value}")
    ...     def h1(self): ...           # declarative -- uses template
    ...
    ...     @renderer()
    ...     def table(self, node, ctx):  # logic -- method is the handler
    ...         return render_table(node)
    ...
    ...     def render(self, built_bag, output=None):
    ...         parts = list(self._walk_render(built_bag))
    ...         return '\\n\\n'.join(p for p in parts if p)
"""
from __future__ import annotations

import inspect
from abc import ABC
from collections import defaultdict
from collections.abc import Callable, Iterator
from typing import Any

from genro_bag import Bag, BagNode

# =============================================================================
# Decorator
# =============================================================================


def _is_empty_body(func: Callable) -> bool:
    """Check if a function has an empty body (only ..., pass, or docstring)."""
    try:
        source = inspect.getsource(func)
    except (OSError, TypeError):
        return False
    lines = [line.strip() for line in source.splitlines()
             if line.strip() and not line.strip().startswith(('#', '@', 'def ', '"""', "'''"))]
    return all(line in ('...', 'pass', '') for line in lines)


def renderer(**kwargs: Any) -> Callable:
    """Decorator to mark a method as render handler for a tag.

    If the method body is empty (...), default_render uses the kwargs
    (e.g. template) to produce output. If the method has logic,
    it IS the render handler.

    Args:
        **kwargs: Render parameters (e.g. template, callback).

    Example:
        @renderer(template="# {node_value}")
        def h1(self): ...

        @renderer()
        def table(self, node, ctx):
            return render_table(node)
    """
    def decorator(func: Callable) -> Callable:
        func._renderer = True  # type: ignore[attr-defined]
        func._renderer_kwargs = kwargs  # type: ignore[attr-defined]
        func._renderer_empty = _is_empty_body(func)  # type: ignore[attr-defined]
        return func
    return decorator


def render_handler(func: Callable) -> Callable:
    """Legacy alias: @render_handler without parentheses."""
    func._renderer = True  # type: ignore[attr-defined]
    func._renderer_kwargs = {}  # type: ignore[attr-defined]
    func._renderer_empty = False  # type: ignore[attr-defined]
    return func


# =============================================================================
# BagRendererBase
# =============================================================================


class BagRendererBase(ABC):
    """Abstract base class for Bag renderers (dead output).

    Provides:
        - @renderer dispatch: tag-based rendering infrastructure
        - _walk_render(), _build_context(), default_render(): rendering utilities
        - render(): main entry point (subclass should override or use as-is)

    Subclasses define render handlers for specific tags using @renderer.
    Empty-body handlers use default_render with decorator kwargs.
    Handlers with logic are called directly.
    """

    _class_render_handlers: dict[str, Callable]
    _class_render_kwargs: dict[str, dict[str, Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Collect @renderer decorated methods."""
        super().__init_subclass__(**kwargs)

        cls._class_render_handlers = {}
        cls._class_render_kwargs = {}

        for parent in cls.__mro__[1:]:
            if hasattr(parent, "_class_render_handlers"):
                cls._class_render_handlers.update(parent._class_render_handlers)
                cls._class_render_kwargs.update(parent._class_render_kwargs)
                break

        for name, obj in cls.__dict__.items():
            if callable(obj) and getattr(obj, "_renderer", False):
                cls._class_render_handlers[name] = obj
                cls._class_render_kwargs[name] = getattr(obj, "_renderer_kwargs", {})

    def __init__(self, builder: Any) -> None:
        """Initialize renderer with builder reference."""
        self.builder = builder
        self._render_handlers = dict(type(self)._class_render_handlers)
        self._render_kwargs = dict(type(self)._class_render_kwargs)

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def render(self, built_bag: Bag, output: Any = None) -> str:
        """Render the built Bag to output string.

        Default implementation walks the bag and joins parts with newlines.
        Override for custom assembly logic.

        Args:
            built_bag: The built Bag to render.
            output: Optional destination (file path, stream, etc.).
                Interpretation depends on the subclass.
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
        1. @renderer with logic body → call method
        2. @renderer with empty body → default_render with kwargs
        3. No handler → default_render with no kwargs
        """
        tag = node.node_tag or node.label
        ctx = self._build_context(node)

        handler = self._render_handlers.get(tag)
        if handler:
            if getattr(handler, "_renderer_empty", False):
                rk = self._render_kwargs.get(tag, {})
                return self.default_render(node, ctx, **rk)
            return handler(self, node, ctx)

        return self.default_render(node, ctx)

    def _build_context(self, node: BagNode) -> dict[str, Any]:
        """Build context dict for render handlers.

        Resolves ^pointer values just-in-time from builder.data.
        The built node is NOT modified — ^pointer strings stay.

        Context contains:
            - node_value: The resolved node value (string)
            - node_label: The node's label
            - _node: The full BagNode (for advanced access)
            - children: Rendered children (if node has Bag value)
            - All resolved node attributes
        """
        resolved = self.builder._resolve_node(node, self.builder.data)
        node_value = resolved["node_value"]

        ctx: dict[str, Any] = {
            "node_value": "" if node_value is None or isinstance(node_value, Bag) else str(node_value),
            "node_label": node.label,
            "_node": node,
        }

        ctx.update(resolved["attrs"])

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

    def default_render(
        self, node: BagNode, ctx: dict[str, Any],
        template: str | None = None, **kwargs: Any,
    ) -> str | None:
        """Default render with optional template.

        Args:
            node: The BagNode being rendered.
            ctx: Context dict with node_value, children, attributes.
            template: Format string with ctx placeholders.
            **kwargs: Additional render parameters from @renderer decorator.
        """
        if template:
            try:
                return template.format_map(defaultdict(str, ctx))
            except (KeyError, ValueError):
                return template

        if ctx["node_value"]:
            return ctx["node_value"]
        if ctx["children"]:
            return ctx["children"]
        return None
