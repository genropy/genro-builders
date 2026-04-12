# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagRendererBase — abstract base class for Bag renderers.

A renderer transforms a built Bag into a serialized output (string, bytes).
It is a "dead" output: no live objects, no reactivity.

Top-down walk with parent (same pattern as the compiler):
    1. handler(self, node, parent) — produce a result
    2. If result is a ``RenderNode``, recurse children into it, then finalize
    3. If result is a ``str``, append to parent (leaf or handler-managed)
    4. If result is ``None``, recurse children into current parent

Handlers read resolved attributes directly from the node:
    ``node.runtime_value`` — resolved value
    ``node.runtime_attrs``  — resolved attributes dict

Pointer formali and just-in-time resolution:
    The built Bag retains ``^pointer`` strings verbatim (pointer formali).
    ``runtime_attrs`` / ``runtime_value`` resolve them just-in-time via
    ``evaluate_on_node(builder.data)``. The renderer works with resolved
    values without modifying the built Bag.

Decorators:
    @renderer: Mark a method as render handler for a specific tag.
               If body is empty (...), delegates to render_node with kwargs.
               If body has logic, the method IS the handler.

Example:
    >>> class MarkdownRenderer(BagRendererBase):
    ...     @renderer(template="# {node_value}")
    ...     def h1(self): ...           # declarative -- uses template
    ...
    ...     @renderer()
    ...     def table(self, node, parent):
    ...         return render_table(node)  # returns str, walk appends to parent
"""
from __future__ import annotations

import inspect
import textwrap
from abc import ABC
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from genro_bag import Bag, BagNode


# =============================================================================
# RenderNode
# =============================================================================


class RenderNode(list):
    """Mutable container that collects rendered children and finalizes to string.

    The handler creates a RenderNode with opening/closing markup.
    The walk fills it with child strings. After all children are
    collected, ``finalize()`` produces the wrapped output.

    This is the renderer equivalent of a "live object" in the compiler:
    children append to it, and it knows how to produce the final string.

    Example:
        >>> rn = RenderNode(before="<div>", after="</div>", indent="  ")
        >>> rn.append("<p>Hello</p>")
        >>> rn.append("<p>World</p>")
        >>> print(rn.finalize())
        <div>
          <p>Hello</p>
          <p>World</p>
        </div>
    """

    def __init__(
        self, before: str = "", after: str = "", value: str = "",
        separator: str = "\n", indent: str = "",
    ) -> None:
        super().__init__()
        self.before = before
        self.after = after
        self.value = value
        self.separator = separator
        self.indent = indent

    def finalize(self) -> str:
        """Produce final string from collected children."""
        parts: list[str] = []
        if self.value:
            parts.append(self.value)
        parts.extend(self)
        inner = self.separator.join(p for p in parts if p)
        if self.indent and inner:
            inner = textwrap.indent(inner, self.indent)
        if self.after:
            if inner:
                return f"{self.before}\n{inner}\n{self.after}"
            return self.before.rstrip()
        return f"{self.before}{inner}" if inner else ""


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

    If the method body is empty (...), render_node uses the kwargs
    (e.g. template) to produce output. If the method has logic,
    it IS the render handler: ``handler(self, node, parent)``.

    Args:
        **kwargs: Render parameters (e.g. template, callback).

    Example:
        @renderer(template="# {node_value}")
        def h1(self): ...

        @renderer()
        def table(self, node, parent):
            return render_table(node)
    """
    def decorator(func: Callable) -> Callable:
        func._renderer = True  # type: ignore[attr-defined]
        func._renderer_kwargs = kwargs  # type: ignore[attr-defined]
        func._renderer_empty = _is_empty_body(func)  # type: ignore[attr-defined]
        return func
    return decorator


# =============================================================================
# BagRendererBase
# =============================================================================


class BagRendererBase(ABC):
    """Abstract base class for Bag renderers (dead output).

    Top-down walk with parent parameter — same pattern as the compiler.
    Handlers receive ``(self, node, parent)`` and return either:

    - ``RenderNode``: container — walk fills it with children, then finalizes
    - ``str``: leaf or fully handled — appended to parent as-is
    - ``None``: transparent — children go directly into current parent

    Handlers read resolved data directly from the node:

    - ``node.runtime_value`` — resolved node value
    - ``node.runtime_attrs`` — resolved attributes dict
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

        Default implementation walks the bag and joins root-level parts.
        Override for custom assembly logic.
        """
        root = self._walk_render(built_bag)
        return "\n".join(p for p in root if p)

    def _walk_render(self, bag: Bag, parent: list | None = None) -> list[str]:
        """Walk bag and render each node via top-down handler dispatch.

        Args:
            bag: The Bag to iterate.
            parent: List collecting rendered strings. Created if None.
        """
        if parent is None:
            parent = []
        for node in bag:
            self._dispatch_render(node, parent)
        return parent

    def _dispatch_render(self, node: BagNode, parent: list) -> None:
        """Render a single node top-down, then recurse into children.

        The handler runs first and returns:
        - RenderNode: container — children fill it, then finalize to string
        - str: leaf — appended to parent, no child recursion
        - None: transparent — children recurse into current parent
        """
        tag = node.node_tag or node.label

        handler = self._render_handlers.get(tag)
        if handler:
            if getattr(handler, "_renderer_empty", False):
                rk = self._render_kwargs.get(tag, {})
                result = self.render_node(node, parent=parent, **rk)
            else:
                result = handler(self, node, parent)
        else:
            result = self.render_node(node, parent=parent)

        # Post-handler: recurse children and finalize
        node_value = node.get_value(static=True)
        has_children = isinstance(node_value, Bag)

        if isinstance(result, RenderNode):
            if has_children:
                self._walk_render(node_value, parent=result)
            parent.append(result.finalize())
        elif isinstance(result, str):
            parent.append(result)
        elif result is None and has_children:
            self._walk_render(node_value, parent=parent)

    # -------------------------------------------------------------------------
    # Default render
    # -------------------------------------------------------------------------

    def render_node(
        self, node: BagNode,
        parent: list | None = None,
        template: str | None = None, **kwargs: Any,
    ) -> str | RenderNode | None:
        """Default render — fallback for tags without a @renderer handler.

        If template is given, builds a dict from runtime_attrs + runtime_value
        and renders the template via format_map. Otherwise returns runtime_value
        if truthy, else None.

        Args:
            node: The BagNode being rendered.
            parent: The parent list collecting rendered strings.
            template: Format string with placeholders.
            **kwargs: Extra parameters from @renderer decorator.
        """
        if template:
            ctx = dict(node.runtime_attrs)
            value = node.runtime_value
            ctx["node_value"] = "" if value is None or isinstance(value, Bag) else str(value)
            ctx["node_label"] = node.label
            try:
                return template.format_map(defaultdict(str, ctx))
            except (KeyError, ValueError):
                return template

        value = node.runtime_value
        if value and not isinstance(value, Bag):
            return str(value)
        return None
