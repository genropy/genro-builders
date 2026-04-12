# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagCompilerBase — abstract base class for Bag compilers.

A compiler transforms a built Bag into live objects (widgets, workbooks,
PDF elements, etc.). It is a "live" output that depends on a runtime.

Top-down walk with parent:
    1. handler(self, node, parent) — produce a compiled object
    2. Recurse children with the handler's result as their parent
    3. The "two roots" walk in parallel: built Bag + compiled object tree

Handlers read resolved attributes directly from the node:
    ``node.runtime_value`` — resolved value
    ``node.runtime_attrs``  — resolved attributes dict

Pointer formali and just-in-time resolution:
    The built Bag retains ``^pointer`` strings verbatim (pointer formali).
    ``runtime_attrs`` / ``runtime_value`` resolve them just-in-time via
    ``evaluate_on_node(builder.data)``. The compiler works with resolved
    values without modifying the built Bag.

Decorators:
    @compiler: Mark a method as compile handler for a specific tag.
               If body is empty (...), delegates to compile_node with kwargs.
               If body has logic, the method IS the handler.

Example:
    >>> class WidgetCompiler(BagCompilerBase):
    ...     @compiler()
    ...     def button(self, node, parent):
    ...         btn = Button(label=node.runtime_value)
    ...         parent.mount(btn)
    ...         return btn  # becomes parent for children
"""
from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Iterator
from typing import Any

from genro_bag import Bag, BagNode

from genro_builders.builder._decorators import _is_empty_body


def compiler(**kwargs: Any) -> Callable:
    """Decorator to mark a method as compile handler for a tag.

    If the method body is empty (...), compile_node uses the kwargs
    to produce output. If the method has logic, it IS the handler:
    ``handler(self, node, parent)``.

    Args:
        **kwargs: Compile parameters passed to compile_node.

    Example:
        @compiler()
        def button(self, node, parent):
            return Button(label=node.runtime_value)
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

    Top-down walk with parent parameter — same pattern as the renderer.
    Handlers receive ``(self, node, parent)`` and return a compiled object.
    Children are then compiled with that object as their parent.

    Handlers read resolved data directly from the node:

    - ``node.runtime_value`` — resolved node value
    - ``node.runtime_attrs`` — resolved attributes dict

    Provides:
        - @compiler dispatch: tag-based compilation infrastructure
        - _walk_compile(), _dispatch_compile(): compilation walk
        - compile_node(): default fallback
        - compile(): main entry point (subclass must override)
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
    # Compilation
    # -------------------------------------------------------------------------

    def compile(self, built_bag: Bag, target: Any = None) -> Any:
        """Compile the built Bag into live objects.

        Subclass must override. Typically calls _walk_compile().
        """
        raise NotImplementedError

    def _walk_compile(self, bag: Bag, parent: Any = None) -> Iterator[Any]:
        """Walk bag and compile each node via top-down handler dispatch.

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

        handler = self._compile_handlers.get(tag)
        if handler:
            if getattr(handler, "_compiler_empty", False):
                ck = self._compile_kwargs.get(tag, {})
                result = self.compile_node(node, parent=parent, **ck)
            else:
                result = handler(self, node, parent)
        else:
            result = self.compile_node(node, parent=parent)

        # Recurse into children with handler's result as parent
        node_value = node.get_value(static=True)
        if isinstance(node_value, Bag):
            child_parent = result if result is not None else parent
            list(self._walk_compile(node_value, parent=child_parent))

        return result

    # -------------------------------------------------------------------------
    # Default compile
    # -------------------------------------------------------------------------

    def compile_node(
        self, node: BagNode,
        parent: Any = None, **kwargs: Any,
    ) -> Any | None:
        """Default compile — fallback for tags without a @compiler handler.

        Returns runtime_value if truthy, else None.

        Args:
            node: The BagNode being compiled.
            parent: The parent compiled object.
            **kwargs: Extra parameters from @compiler decorator.
        """
        value = node.runtime_value
        if value and not isinstance(value, Bag):
            return value
        return None
