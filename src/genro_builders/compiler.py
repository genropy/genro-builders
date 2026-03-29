# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagCompilerBase — abstract base class for Bag compilers.

A compiler has two distinct responsibilities:

1. **compile(source, target, data, binding)** → None:
   Single recursive walk: for each node, expand components (via resolvers),
   resolve ^pointers against data, register subscriptions in the binding
   map, recurse into children. Populates the built (target) Bag.

2. **Rendering** (subclass-defined):
   Transform the built Bag into an output format (HTML, YAML, etc.)
   or into live objects (Textual widgets, openpyxl workbooks, etc.).
   Subclasses define their own rendering methods, optionally using
   @compile_handler for tag-based dispatch.

Decorators:
    @compile_handler: Mark a method as render handler for a specific tag.
                      Used by _walk_compile() for automatic tag dispatch.

Example:
    >>> class MarkdownCompiler(BagCompilerBase):
    ...     @compile_handler
    ...     def h1(self, node, ctx):
    ...         return f"# {ctx['node_value']}"
    ...
    ...     def to_markdown(self, built_bag):
    ...         parts = list(self._walk_compile(built_bag))
    ...         return '\\n\\n'.join(p for p in parts if p)
"""
from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Iterator
from typing import Any

from genro_bag import Bag, BagNode

from .pointer import scan_for_pointers

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
        - compile(): Single recursive walk — expand, resolve, register
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
    # compile() — single recursive walk
    # -------------------------------------------------------------------------

    def compile(
        self,
        source: Bag,
        target: Bag,
        data: Bag,
        binding: Any,
        prefix: str = "",
    ) -> None:
        """Compile source into target: expand, resolve pointers, register map.

        Single recursive walk. For each node:
        1. Clean subscription map for the subtree being compiled
        2. Expand component if resolver present
        3. Create node in target
        4. Resolve ^pointers against data and register in binding map
        5. Recurse into children (Bag values)

        The same method handles full compile (from root) and incremental
        compile (from a subtree). The unbind_path at each node ensures
        stale entries are cleaned before re-registering.

        Args:
            source: The source Bag to compile from.
            target: The built Bag to populate.
            data: Data Bag for ^pointer resolution.
            binding: BindingManager for subscription registration.
            prefix: Path prefix for subscription map keys.
        """
        from .builder_bag import BuilderBag

        for node in source:
            built_path = f"{prefix}.{node.label}" if prefix else node.label

            # 1. Clean subscription map for this subtree
            binding.unbind_path(built_path)

            # 2. Expand component if resolver present
            value = node.get_value(static=False) if node.resolver is not None else node.static_value

            # 3. Create node in target
            new_node = target.set_item(
                node.label,
                value if not isinstance(value, Bag) else BuilderBag(builder=type(self.builder)),
                _attributes=dict(node.attr),
                node_tag=node.node_tag,
            )

            # 4. Resolve ^pointers and register in map
            self._resolve_and_register(new_node, built_path, data, binding)

            # 5. Recurse into children
            if isinstance(value, Bag):
                self.compile(value, new_node.value, data, binding, prefix=built_path)

    # -------------------------------------------------------------------------
    # Pointer resolution and registration
    # -------------------------------------------------------------------------

    def _resolve_and_register(
        self, node: BagNode, built_path: str, data: Bag, binding: Any,
    ) -> None:
        """Resolve ^pointers on a node and register subscriptions in the map.

        Args:
            node: The built BagNode to process.
            built_path: The absolute path of this node in the built bag.
            data: Data Bag for ^pointer resolution.
            binding: BindingManager for subscription registration.
        """
        pointers = scan_for_pointers(node)
        if not pointers:
            return

        for pointer_info, location in pointers:
            # Resolve datapath for relative pointers
            datapath = ""
            if pointer_info.is_relative and hasattr(node, "_resolve_datapath"):
                datapath = node._resolve_datapath()

            # Compute absolute data path
            data_path = pointer_info.path
            if pointer_info.is_relative:
                rel = data_path[1:]  # strip leading '.'
                data_path = f"{datapath}.{rel}" if datapath else rel

            # Resolve value from data and apply (only if found)
            resolved = self._resolve_pointer(node, pointer_info, data_path, data)
            if resolved is not None:
                if location == "value":
                    node.set_value(resolved, trigger=False)
                elif location.startswith("attr:"):
                    attr_name = location[5:]
                    node.set_attr({attr_name: resolved}, trigger=False)

            # Build map keys and register
            data_key = f"{data_path}?{pointer_info.attr}" if pointer_info.attr else data_path
            built_entry = built_path if location == "value" else f"{built_path}?{location[5:]}"

            binding.register(data_key, built_entry)

    def _resolve_pointer(
        self, node: BagNode, pointer_info: Any, data_path: str, data: Bag,
    ) -> Any:
        """Resolve a single ^pointer value from the data Bag."""
        if hasattr(node, "_get_relative_data"):
            return node._get_relative_data(data, pointer_info.raw[1:])  # strip ^

        if pointer_info.attr:
            data_node = data.get_node(data_path)
            return data_node.attr.get(pointer_info.attr) if data_node else None
        return data.get_item(data_path)

    # -------------------------------------------------------------------------
    # Rendering utilities (for subclass use)
    # -------------------------------------------------------------------------

    def _walk_compile(self, bag: Bag) -> Iterator[str]:
        """Walk bag and render each node via handler dispatch."""
        for node in bag:
            result = self._render_node(node)
            if result is not None:
                yield result

    def _render_node(self, node: BagNode) -> str | None:
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
            info = self.builder._get_schema_info(tag)
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
