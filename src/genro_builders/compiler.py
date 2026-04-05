# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagCompilerBase — abstract base class for Bag compilers (live output).

A compiler transforms a built Bag into live objects (Textual widgets,
openpyxl workbooks, etc.). For serialized output (strings, bytes),
use BagRendererBase instead.

Pointer formali and just-in-time resolution:
    Like renderers, compilers work with pointer formali: the built Bag
    retains ``^pointer`` strings verbatim. During ``_walk_compile()``,
    each node is resolved just-in-time via ``builder._resolve_node()``
    which returns resolved ``node_value`` and ``attrs``. Compilers
    produce live objects from the resolved data without modifying
    the built Bag.

Decorators:
    @compiler: Mark a method as compile handler for a specific tag.
               If body is empty (...), uses default_compile with kwargs.
               If body has logic, the method IS the handler.

Example:
    >>> class TextualCompiler(BagCompilerBase):
    ...     @compiler(module="textual.widgets", cls="Button")
    ...     def button(self): ...           # declarative
    ...
    ...     @compiler()
    ...     def datatable(self, node, ctx):  # logic
    ...         return build_datatable(node)
    ...
    ...     def compile(self, built_bag, target=None):
    ...         return list(self._walk_compile(built_bag))
"""
from __future__ import annotations

import inspect
from abc import ABC
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


def compiler(**kwargs: Any) -> Callable:
    """Decorator to mark a method as compile handler for a tag.

    If the method body is empty (...), default_compile uses the kwargs
    (e.g. module, cls) to produce output. If the method has logic,
    it IS the compile handler.

    Args:
        **kwargs: Compile parameters (e.g. module, cls).

    Example:
        @compiler(module="textual.widgets", cls="Button")
        def button(self): ...

        @compiler()
        def datatable(self, node, ctx):
            return build_datatable(node)
    """
    def decorator(func: Callable) -> Callable:
        func._compiler = True  # type: ignore[attr-defined]
        func._compiler_kwargs = kwargs  # type: ignore[attr-defined]
        func._compiler_empty = _is_empty_body(func)  # type: ignore[attr-defined]
        return func
    return decorator


def compile_handler(func: Callable) -> Callable:
    """Legacy alias: @compile_handler without parentheses."""
    func._compiler = True  # type: ignore[attr-defined]
    func._compiler_kwargs = {}  # type: ignore[attr-defined]
    func._compiler_empty = False  # type: ignore[attr-defined]
    return func


# =============================================================================
# BagCompilerBase
# =============================================================================


class BagCompilerBase(ABC):
    """Abstract base class for Bag compilers (live output).

    Provides:
        - @compiler dispatch: tag-based compilation infrastructure
        - _walk_compile(), _build_context(), default_compile(): utilities
        - compile(): main entry point (subclass must override)

    Subclasses define compile handlers for specific tags using @compiler.
    Empty-body handlers use default_compile with decorator kwargs.
    Handlers with logic are called directly.
    """

    _class_compile_handlers: dict[str, Callable]
    _class_compile_kwargs: dict[str, dict[str, Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Collect @compiler decorated methods."""
        super().__init_subclass__(**kwargs)

        cls._class_compile_handlers = {}
        cls._class_compile_kwargs = {}

        for parent in cls.__mro__[1:]:
            if hasattr(parent, "_class_compile_handlers"):
                cls._class_compile_handlers.update(parent._class_compile_handlers)
                cls._class_compile_kwargs.update(parent._class_compile_kwargs)
                break

        for name, obj in cls.__dict__.items():
            if callable(obj) and getattr(obj, "_compiler", False):
                cls._class_compile_handlers[name] = obj
                cls._class_compile_kwargs[name] = getattr(obj, "_compiler_kwargs", {})

    def __init__(self, builder: Any) -> None:
        """Initialize compiler with builder reference."""
        self.builder = builder
        self._compile_handlers = dict(type(self)._class_compile_handlers)
        self._compile_kwargs = dict(type(self)._class_compile_kwargs)

    # -------------------------------------------------------------------------
    # Compilation (subclass must override)
    # -------------------------------------------------------------------------

    def compile(self, built_bag: Bag, target: Any = None) -> Any:
        """Transform built Bag into live objects. Subclass must override.

        Args:
            built_bag: The built Bag to compile.
            target: Optional target (parent widget, container, etc.).
                Interpretation depends on the subclass.
        """
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
        1. @compiler with logic body → call method
        2. @compiler with empty body → default_compile with kwargs
        3. No handler → default_compile with no kwargs
        """
        tag = node.node_tag or node.label
        ctx = self._build_context(node)

        handler = self._compile_handlers.get(tag)
        if handler:
            if getattr(handler, "_compiler_empty", False):
                ck = self._compile_kwargs.get(tag, {})
                return self.default_compile(node, ctx, **ck)
            return handler(self, node, ctx)

        return self.default_compile(node, ctx)

    def _build_context(self, node: BagNode) -> dict[str, Any]:
        """Build context dict for compile handlers.

        Resolves ^pointer values just-in-time from builder.data.
        The built node is NOT modified — ^pointer strings stay.

        Context contains:
            - node_value: The resolved node value (string)
            - node_label: The node's label
            - _node: The full BagNode (for advanced access)
            - children: Compiled children (if node has Bag value)
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
            ctx["children"] = list(self._walk_compile(node_value))
        else:
            ctx["children"] = []

        return ctx

    # -------------------------------------------------------------------------
    # Default compile
    # -------------------------------------------------------------------------

    def default_compile(
        self, node: BagNode, ctx: dict[str, Any], **kwargs: Any,
    ) -> Any | None:
        """Default compile with optional kwargs from @compiler decorator.

        Override in subclass for custom default behavior (e.g. widget
        instantiation from module/cls kwargs).
        """
        if ctx["node_value"]:
            return ctx["node_value"]
        if ctx["children"]:
            return ctx["children"]
        return None
