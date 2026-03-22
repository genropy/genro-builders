# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagCompilerBase - Abstract base class for Bag compilers.

Compilers transform a Bag (built with a Builder) into output formats.
The compile flow is:

    1. preprocess(bag) - Expand components, normalize parameters
    2. walk + compile handlers - Transform each node to output
    3. Return final output

Decorators:
    @compile_handler: Mark a method as compile handler for a specific tag.
                      If no @compile_handler method matches, default_compile is used.

Example:
    >>> from genro_bag.compiler import BagCompilerBase, compile_handler
    >>>
    >>> class MarkdownCompiler(BagCompilerBase):
    ...     @compile_handler
    ...     def h1(self, node, ctx):
    ...         return f"# {ctx['node_value']}"
    ...
    ...     @compile_handler
    ...     def blockquote(self, node, ctx):
    ...         lines = ctx['node_value'].split('\\n')
    ...         return '\\n'.join(f'> {line}' for line in lines)
    ...
    ...     # Other tags use default_compile with compile_template from schema
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from genro_bag import Bag, BagNode


# =============================================================================
# Decorator
# =============================================================================


def compile_handler(func: Callable) -> Callable:
    """Decorator to mark a method as compile handler for a tag.

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

    Subclasses define @compile_handler methods for specific tags.
    Tags without a @compile_handler method use default_compile().

    The compile flow:
        1. preprocess() - Called first, expands components (lazy expansion)
        2. _walk_compile() - Walk bag, call handlers for each node
        3. default_compile() - Fallback using compile_kwargs from schema

    Attributes:
        builder: The builder instance (provides schema access).
        _compile_handlers: Dict mapping tag names to handler methods.
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
    # Main compile entry point
    # -------------------------------------------------------------------------

    def compile(self, bag: Bag | None = None) -> str:
        """Compile bag to output format.

        Args:
            bag: The Bag to compile. If None, uses builder.bag.

        Returns:
            Compiled output (string by default, subclasses may vary).
        """
        if bag is None:
            bag = self.builder.bag

        # 1. Preprocess (expand components, normalize, etc.)
        processed_bag = self.preprocess(bag)

        # 2. Walk and compile
        parts = list(self._walk_compile(processed_bag))

        # 3. Join output
        return self.join_output(parts)

    def join_output(self, parts: list[str]) -> str:
        """Join compiled parts into final output.

        Override in subclasses for different joining logic.
        Default: join with double newline.
        """
        return "\n\n".join(p for p in parts if p)

    # -------------------------------------------------------------------------
    # Preprocess
    # -------------------------------------------------------------------------

    def preprocess(self, bag: Bag) -> Bag:
        """Preprocess bag before compilation.

        Default implementation expands components if present.
        Override for custom preprocessing.

        Args:
            bag: The source Bag.

        Returns:
            Preprocessed Bag (may be same instance if no changes).
        """
        # Check if any component needs expansion
        has_components = self._has_components(bag)
        if not has_components:
            return bag

        # Expand components
        return self._expand_components(bag)

    def _has_components(self, bag: Bag) -> bool:
        """Check if bag contains any unexpanded components."""
        return any(node.tag and self._is_component(node) for _path, node in bag.walk())

    def _is_component(self, node: BagNode) -> bool:
        """Check if node is a component that needs expansion."""
        if not node.tag:
            return False
        try:
            info = self.builder.get_schema_info(node.tag)
            return info.get("is_component", False)
        except KeyError:
            return False

    def _expand_components(self, bag: Bag) -> Bag:
        """Expand all components in bag.

        Creates a new Bag with components replaced by their expanded content.
        """
        from .builder_bag import BuilderBag

        result = BuilderBag(builder=type(self.builder))

        for node in bag:
            if self._is_component(node):
                # Get component handler from builder
                info = self.builder.get_schema_info(node.tag)
                handler_name = info.get("handler_name")
                if handler_name:
                    handler = getattr(self.builder, handler_name)
                    # Create temp bag for expansion
                    component_bag = BuilderBag(builder=type(self.builder))
                    # Call handler with kwargs from node attributes
                    kwargs = dict(node.attr)
                    handler(component_bag, **kwargs)
                    # Recursively expand and merge
                    expanded = self._expand_components(component_bag)
                    for child in expanded:
                        result.set_item(
                            child.label,
                            child.value,
                            _attributes=dict(child.attr),
                        )
                        result.get_node(child.label).tag = child.tag
            else:
                # Copy node, recursively expand children if Bag
                value = node.value
                if isinstance(value, Bag):
                    value = self._expand_components(value)
                new_node = result.set_item(
                    node.label,
                    value,
                    _attributes=dict(node.attr),
                )
                new_node.tag = node.tag

        return result

    # -------------------------------------------------------------------------
    # Walk and compile
    # -------------------------------------------------------------------------

    def _walk_compile(self, bag: Bag) -> Iterator[str]:
        """Walk bag and compile each node."""
        for node in bag:
            result = self._compile_node(node)
            if result is not None:
                yield result

    def _compile_node(self, node: BagNode) -> str | None:
        """Compile a single node.

        Resolution order:
        1. compile_handler from schema (explicit override)
        2. @compile_handler method matching tag name
        3. default_compile()
        """
        tag = node.tag or node.label

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
        """Build context dict for compile handlers.

        Context contains:
            - node_value: The node's value (string)
            - node_label: The node's label
            - _node: The full BagNode (for advanced access)
            - children: Compiled children (if node has Bag value)
            - All node attributes
        """
        from genro_bag import Bag

        node_value = node.get_value(static=True)
        node_value = "" if node_value is None else str(node_value)

        ctx: dict[str, Any] = {
            "node_value": node_value,
            "node_label": node.label,
            "_node": node,
        }

        # Add all node attributes
        ctx.update(node.attr)

        # Compile children if value is a Bag
        if isinstance(node.value, Bag):
            children_parts = list(self._walk_compile(node.value))
            ctx["children"] = self.join_children(children_parts)
        else:
            ctx["children"] = ""

        return ctx

    def join_children(self, parts: list[str]) -> str:
        """Join compiled children.

        Override for different child joining logic.
        Default: join with newline.
        """
        return "\n".join(p for p in parts if p)

    # -------------------------------------------------------------------------
    # Default compile
    # -------------------------------------------------------------------------

    def default_compile(
        self, node: BagNode, ctx: dict[str, Any], info: dict[str, Any]
    ) -> str | None:
        """Default compile using compile_kwargs from schema.

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
