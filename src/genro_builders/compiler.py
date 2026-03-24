# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagCompilerBase - Abstract base class for Bag compilers.

A compiler has two distinct responsibilities:

1. **compile(bag, data)** → CompiledBag:
   Expand components (via resolvers) and resolve ^pointers against data.
   The result is a static, fully resolved Bag — the CompiledBag.

2. **Rendering** (subclass-defined):
   Transform the CompiledBag into an output format (HTML, YAML, etc.).
   Subclasses define their own rendering methods, optionally using
   @compile_handler for tag-based dispatch.

The CompiledBag is the contract between compilation and rendering.
Multiple renderers can consume the same CompiledBag.

Decorators:
    @compile_handler: Mark a method as render handler for a specific tag.
                      Used by _walk_compile() for automatic tag dispatch.

Example:
    >>> class MarkdownCompiler(BagCompilerBase):
    ...     @compile_handler
    ...     def h1(self, node, ctx):
    ...         return f"# {ctx['node_value']}"
    ...
    ...     def to_markdown(self, compiled_bag):
    ...         parts = list(self._walk_compile(compiled_bag))
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


def compile_handler(func: Callable) -> Callable:
    """Decorator to mark a method as render handler for a tag.

    The method name becomes the tag it handles.

    Args:
        func: Method to decorate. Name should match the tag.

    Example:
        @compile_handler
        def h1(self, node, ctx):
            return f"# {ctx['node_value']}"
    """
    func._compile_handler = True  # type: ignore[attr-defined]
    return func


# =============================================================================
# BagCompilerBase
# =============================================================================


class BagCompilerBase(ABC):
    """Abstract base class for Bag compilers.

    Provides:
        - compile(): Expand components + resolve pointers → CompiledBag
        - @compile_handler dispatch: tag-based rendering infrastructure
        - _walk_compile(), _build_context(), default_compile(): rendering utilities

    Subclasses use these to build their own output methods (to_html, to_yaml, etc.).
    """

    _class_compile_handlers: dict[str, Callable]  # Built at class definition

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Collect @compile_handler decorated methods into _class_compile_handlers."""
        super().__init_subclass__(**kwargs)

        cls._class_compile_handlers = {}

        # Inherit from parent
        for parent in cls.__mro__[1:]:
            if hasattr(parent, "_class_compile_handlers"):
                cls._class_compile_handlers.update(parent._class_compile_handlers)
                break

        # Collect @compile_handler methods from this class
        for name, obj in cls.__dict__.items():
            if callable(obj) and getattr(obj, "_compile_handler", False):
                cls._class_compile_handlers[name] = obj

    def __init__(self, builder: Any) -> None:
        """Initialize compiler with builder reference.

        Args:
            builder: The BagBuilderBase instance that built the bag.
        """
        self.builder = builder
        self._compile_handlers = dict(type(self)._class_compile_handlers)

    # -------------------------------------------------------------------------
    # compile() → CompiledBag
    # -------------------------------------------------------------------------

    def compile(
        self, bag: Bag | None = None, data: Bag | None = None, target: Bag | None = None,
    ) -> Bag:
        """Compile a BuilderBag into a CompiledBag.

        Expands all components (via resolvers) and resolves ^pointers
        against data. The result is a static, fully resolved Bag.

        Args:
            bag: The Bag to compile. If None, uses builder.bag.
            data: Optional data Bag for ^pointer resolution.
                If None, pointers are left as-is.
            target: Optional target Bag to materialize into. If provided,
                nodes are added to this Bag instead of creating a new one.

        Returns:
            CompiledBag — a static Bag with components expanded and
            pointers resolved. Ready for rendering.
        """
        if bag is None:
            bag = self.builder.bag

        # 1. Materialize components
        compiled = self._materialize(bag, target=target)

        # 2. Resolve pointers
        if data is not None:
            self._resolve_pointers(compiled, data)

        return compiled

    # -------------------------------------------------------------------------
    # Materialization (component expansion)
    # -------------------------------------------------------------------------

    def _materialize(self, bag: Bag, target: Bag | None = None) -> Bag:
        """Create a static copy of the bag with all resolvers expanded.

        Args:
            bag: The source Bag to materialize.
            target: Optional target Bag to populate. If None, creates a new one.
        """
        from .builder_bag import BuilderBag

        result = target if target is not None else BuilderBag(builder=type(self.builder))

        for node in bag:
            value = node.get_value(static=False) if node.resolver is not None else node.static_value
            if isinstance(value, Bag):
                value = self._materialize(value)
            result.set_item(
                node.label,
                value,
                _attributes=dict(node.attr),
                node_tag=node.node_tag,
            )

        return result

    # -------------------------------------------------------------------------
    # Pointer resolution
    # -------------------------------------------------------------------------

    def _resolve_pointers(self, bag: Bag, data: Bag) -> None:
        """Resolve all ^pointers in-place against data."""
        from .pointer import scan_for_pointers

        for node in bag:
            pointers = scan_for_pointers(node)
            for pointer_info, location in pointers:
                if hasattr(node, "get_relative_data"):
                    resolved = node.get_relative_data(data, pointer_info.raw[1:])
                else:
                    resolved = data.get_item(pointer_info.path)

                if location == "value":
                    node.set_value(resolved, trigger=False)
                elif location.startswith("attr:"):
                    attr_name = location[5:]
                    node.set_attr({attr_name: resolved}, trigger=False)

            # Recurse into children
            value = node.static_value
            if isinstance(value, Bag):
                self._resolve_pointers(value, data)

    # -------------------------------------------------------------------------
    # Rendering utilities (for subclass use)
    # -------------------------------------------------------------------------

    def _walk_compile(self, bag: Bag) -> Iterator[str]:
        """Walk bag and render each node via handler dispatch."""
        for node in bag:
            result = self._compile_node(node)
            if result is not None:
                yield result

    def _compile_node(self, node: BagNode) -> str | None:
        """Render a single node.

        Resolution order:
        1. compile_handler from schema (explicit override)
        2. @compile_handler method matching tag name
        3. default_compile()
        """
        tag = node.node_tag or node.label

        # Build context
        ctx = self._build_context(node)

        # 1. Check for explicit compile_handler in schema
        try:
            info = self.builder.get_schema_info(tag)
            handler_name = info.get("compile_kwargs", {}).get("handler")
            if handler_name:
                handler = getattr(self, handler_name, None)
                if handler:
                    return handler(node, ctx)
        except KeyError:
            info = {}

        # 2. Check for @compile_handler method
        handler = self._compile_handlers.get(tag)
        if handler:
            return handler(self, node, ctx)

        # 3. Use default_compile
        return self.default_compile(node, ctx, info)

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

        # Add all node attributes
        ctx.update(node.attr)

        # Render children if value is a Bag
        if isinstance(node_value, Bag):
            children_parts = list(self._walk_compile(node_value))
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

    def default_compile(
        self, node: BagNode, ctx: dict[str, Any], info: dict[str, Any]
    ) -> str | None:
        """Default render using compile_kwargs from schema.

        Checks for:
        - compile_template: Format string with ctx placeholders
        - compile_callback: Method name to call (modifies ctx in place)

        If neither, returns node_value or children.
        """
        compile_kwargs = info.get("compile_kwargs", {})

        # Check for callback (modifies ctx)
        callback_name = compile_kwargs.get("callback")
        if callback_name:
            callback = getattr(self, callback_name, None)
            if callback:
                callback(ctx)

        # Check for template
        template = compile_kwargs.get("template")
        if template:
            try:
                return template.format(**ctx)
            except KeyError:
                # Missing placeholder, return as-is
                return template

        # No template: return value or children
        if ctx["node_value"]:
            return ctx["node_value"]
        if ctx["children"]:
            return ctx["children"]

        return None
