# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagCompilerBase — abstract base class for Bag compilers (live output).

A compiler transforms a built Bag into live objects (Textual widgets,
openpyxl workbooks, etc.). For serialized output (strings, bytes),
use BagRendererBase instead.

Decorators:
    @compile_handler: Mark a method as compile handler for a specific tag.
                      Used by _walk_compile() for automatic tag dispatch.

Example:
    >>> class TextualCompiler(BagCompilerBase):
    ...     @compile_handler
    ...     def button(self, node, ctx):
    ...         from textual.widgets import Button
    ...         return Button(ctx['node_value'])
    ...
    ...     def compile(self, built_bag):
    ...         return list(self._walk_compile(built_bag))
"""
from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Iterator
from typing import Any

from genro_bag import Bag, BagNode

# =============================================================================
# Decorator
# =============================================================================


def compile_handler(func: Callable) -> Callable:
    """Decorator to mark a method as compile handler for a tag.

    The method name becomes the tag it handles.

    Example:
        @compile_handler
        def button(self, node, ctx):
            from textual.widgets import Button
            return Button(ctx['node_value'])
    """
    func._compile_handler = True  # type: ignore[attr-defined]
    return func


# =============================================================================
# BagCompilerBase
# =============================================================================


class BagCompilerBase(ABC):
    """Abstract base class for Bag compilers (live output).

    Provides:
        - @compile_handler dispatch: tag-based compilation infrastructure
        - _walk_compile(), _build_context(), default_compile(): utilities
        - compile(): main entry point (subclass must override)

    Subclasses define compile handlers for specific tags and implement
    compile() to produce live objects from the built Bag.
    """

    _class_compile_handlers: dict[str, Callable]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Collect @compile_handler decorated methods into _class_compile_handlers."""
        super().__init_subclass__(**kwargs)

        cls._class_compile_handlers = {}

        for parent in cls.__mro__[1:]:
            if hasattr(parent, "_class_compile_handlers"):
                cls._class_compile_handlers.update(parent._class_compile_handlers)
                break

        for name, obj in cls.__dict__.items():
            if callable(obj) and getattr(obj, "_compile_handler", False):
                cls._class_compile_handlers[name] = obj

    def __init__(self, builder: Any) -> None:
        """Initialize compiler with builder reference.

        Args:
            builder: The BagBuilderBase instance that owns this compiler.
        """
        self.builder = builder
        self._compile_handlers = dict(type(self)._class_compile_handlers)

    # -------------------------------------------------------------------------
    # Compilation (subclass must override)
    # -------------------------------------------------------------------------

    def compile(self, built_bag: Bag) -> Any:
        """Transform built Bag into live objects. Subclass must override."""
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Compilation utilities (for subclass use)
    # -------------------------------------------------------------------------

    def _walk_compile(self, bag: Bag) -> Iterator[Any]:
        """Walk bag and compile each node via handler dispatch."""
        for node in bag:
            result = self._compile_node(node)
            if result is not None:
                yield result

    def _compile_node(self, node: BagNode) -> Any | None:
        """Compile a single node.

        Resolution order:
        1. @compile_handler method matching tag name
        2. default_compile()
        """
        tag = node.node_tag or node.label
        ctx = self._build_context(node)

        handler = self._compile_handlers.get(tag)
        if handler:
            return handler(self, node, ctx)

        return self.default_compile(node, ctx)

    def _build_context(self, node: BagNode) -> dict[str, Any]:
        """Build context dict for compile handlers.

        Context contains:
            - node_value: The node's value (string)
            - node_label: The node's label
            - _node: The full BagNode (for advanced access)
            - children: Compiled children (if node has Bag value)
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
            ctx["children"] = list(self._walk_compile(node_value))
        else:
            ctx["children"] = []

        return ctx

    # -------------------------------------------------------------------------
    # Default compile
    # -------------------------------------------------------------------------

    def default_compile(self, node: BagNode, ctx: dict[str, Any]) -> Any | None:
        """Default compile: return value, children, or None. Override in subclass."""
        if ctx["node_value"]:
            return ctx["node_value"]
        if ctx["children"]:
            return ctx["children"]
        return None
