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
               If body is empty (...), delegates to compile_node with kwargs.
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

    If the method body is empty (...), compile_node uses the kwargs
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


# =============================================================================
# BagCompilerBase
# =============================================================================


class BagCompilerBase(ABC):
    """Abstract base class for Bag compilers (live output).

    Provides:
        - @compiler dispatch: tag-based compilation infrastructure
        - _walk_compile(), _resolve_context(): compilation infrastructure
        - compile_node(): override this to define how a single node is compiled
        - compile(): main entry point (subclass must override)

    Subclasses define compile handlers for specific tags using @compiler.
    Empty-body handlers use compile_node with decorator kwargs.
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

    def _walk_compile(self, bag: Bag, parent: Any = None) -> Iterator[Any]:
        """Walk bag and compile each node via handler dispatch.

        Args:
            bag: The Bag to iterate.
            parent: The parent compiled object, passed to each handler.
        """
        for node in bag:
            result = self._dispatch_compile(node, parent=parent)
            if result is not None:
                yield result

    def _dispatch_compile(self, node: BagNode, parent: Any = None) -> Any | None:
        """Compile a single node, then recurse into children.

        Top-down: the handler runs first and returns a compiled object.
        If the node has children, they are compiled with the handler's
        result as their parent (two roots walking in parallel).

        Args:
            node: The built BagNode to compile.
            parent: The parent compiled object (e.g. Workbook, Widget).
        """
        tag = node.node_tag or node.label
        ctx = self._resolve_context(node)

        handler = self._compile_handlers.get(tag)
        if handler:
            if getattr(handler, "_compiler_empty", False):
                ck = self._compile_kwargs.get(tag, {})
                result = self.compile_node(node, ctx, parent=parent, **ck)
            else:
                result = handler(self, node, ctx, parent)
        else:
            result = self.compile_node(node, ctx, parent=parent)

        # Recurse into children with handler's result as parent
        node_value = node.get_value(static=True)
        if isinstance(node_value, Bag):
            child_parent = result if result is not None else parent
            list(self._walk_compile(node_value, parent=child_parent))

        return result

    def _resolve_context(self, node: BagNode) -> dict[str, Any]:
        """Resolve node attributes into a context dict.

        Resolves ^pointer values just-in-time from builder.data.
        The built node is NOT modified — ^pointer strings stay.
        Does NOT process children — that is the caller's responsibility.

        Context contains:
            - node_value: The resolved node value (string)
            - node_label: The node's label
            - _node: The full BagNode (for advanced access)
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
        return ctx

    # -------------------------------------------------------------------------
    # Default compile
    # -------------------------------------------------------------------------

    def compile_node(
        self, node: BagNode, ctx: dict[str, Any],
        parent: Any = None, **kwargs: Any,
    ) -> Any | None:
        """Default compile — fallback for tags without a @compiler handler.

        Returns node_value if truthy, else children list if non-empty,
        else None.

        Args:
            node: The BagNode being compiled.
            ctx: Context dict with resolved attributes.
            parent: The parent compiled object (e.g. Workbook, Widget).
            **kwargs: Extra parameters from @compiler decorator.
        """
        if ctx["node_value"]:
            return ctx["node_value"]
        return None
