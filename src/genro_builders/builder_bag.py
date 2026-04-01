# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderBag and BuilderBagNode - Bag subclasses with builder support.

BuilderBag extends Bag to support domain-specific builders that define
grammars for creating nodes. BuilderBagNode extends BagNode to delegate
attribute access to the builder.

Example:
    >>> from genro_builders import BuilderBag
    >>> from genro_builders.builders import HtmlBuilder
    >>> html = BuilderBag(builder=HtmlBuilder)
    >>> html.div(id='main').p(value='Hello')
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode
from genro_toolbox.decorators import extract_kwargs

_BUILDERBAG_PROTECTED = frozenset({"builder", "node_class"})


class BuilderBagNode(BagNode):
    """BagNode with builder delegation and data resolution.

    When a builder is attached to the parent Bag, allows calling
    builder methods directly on nodes to add children:

        node = bag.div()  # returns BuilderBagNode
        node.span()       # delegates to builder._command_on_node()

    Data resolution methods resolve paths relative to this node's
    position in the tree, using the ``datapath`` attribute chain:

        node._get_relative_data(data, '.name')   # relative to this node's datapath
        node._get_relative_data(data, 'user.name')  # absolute
        node._set_relative_data(data, '.name', 'value')
    """

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to builder if available."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        builder = self._parent_bag._builder if self._parent_bag is not None else None

        if builder is not None:
            return lambda node_value=None, node_position=None, **attrs: builder._command_on_node(
                self, name, node_position=node_position, node_value=node_value, **attrs
            )

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __dir__(self) -> list[str]:
        """Return allowed child tags for autocompletion.

        Uses the node's node_tag to look up sub_tags_compiled in the
        builder schema, returning only the tags that are valid children.
        """
        base = set(super().__dir__())
        builder = self._parent_bag._builder if self._parent_bag is not None else None
        if builder is None or not self.node_tag:
            return sorted(base)

        info = builder._get_schema_info(self.node_tag)
        sub_tags = info.get("sub_tags")
        if sub_tags == "":
            return sorted(base)

        sub_tags_compiled = info.get("sub_tags_compiled")
        if isinstance(sub_tags_compiled, dict):
            base.update(sub_tags_compiled.keys())
        elif sub_tags_compiled == "*" or sub_tags is None:
            for schema_node in builder._schema:
                name = schema_node.label
                if not name.startswith("@"):
                    base.add(name)
        return sorted(base)

    # -------------------------------------------------------------------------
    # Data resolution
    # -------------------------------------------------------------------------

    def _get_relative_data(self, data: Bag, path: str) -> Any:
        """Resolve a data path from this node's perspective.

        Args:
            data: The data Bag to read from.
            path: Data path to resolve. Syntax:
                'alfa.beta'       — absolute: data['alfa.beta']
                '.beta'           — relative to this node's datapath
                'alfa.beta?color' — attribute 'color' of data node 'alfa.beta'
                '.beta?color'     — relative + attribute

        Returns:
            The resolved value or attribute.
        """
        resolved_path, attr_name = self._resolve_path(path)
        if attr_name is not None:
            node = data.get_node(resolved_path)
            if node is None:
                return None
            return node.attr.get(attr_name)
        return data.get_item(resolved_path)

    def _set_relative_data(self, data: Bag, path: str, value: Any) -> None:
        """Set a value in the data Bag from this node's perspective.

        Args:
            data: The data Bag to write to.
            path: Data path to resolve (same syntax as get_relative_data).
            value: The value to set.
        """
        resolved_path, attr_name = self._resolve_path(path)
        if attr_name is not None:
            data.set_attr(resolved_path, **{attr_name: value})
        else:
            data.set_item(resolved_path, value)

    def _resolve_path(self, path: str) -> tuple[str, str | None]:
        """Parse and resolve a data path.

        Returns:
            Tuple of (resolved_path, attr_name_or_none).
        """
        attr_name = None
        if "?" in path:
            path, attr_name = path.split("?", 1)

        if path.startswith("."):
            datapath = self._resolve_datapath()
            path = f"{datapath}.{path[1:]}" if datapath else path[1:]

        return path, attr_name

    def _resolve_datapath(self) -> str:
        """Compose hierarchical datapath by walking up the ancestor chain.

        Collects ``datapath`` attributes from ancestor nodes. Relative
        datapaths (starting with '.') are concatenated; absolute datapaths
        reset the chain.
        """
        parts: list[str] = []
        current_bag = self._parent_bag

        while current_bag is not None:
            node = current_bag.parent_node
            if node is None:
                break
            dp = node.attr.get("datapath", "")
            if dp:
                parts.append(dp)
                if not dp.startswith("."):
                    break
            current_bag = node._parent_bag

        parts.reverse()

        result = ""
        for part in parts:
            if part.startswith("."):
                result = f"{result}.{part[1:]}" if result else part[1:]
            else:
                result = part
        return result


class BuilderBag(Bag):
    """Bag with builder support.

    Extends Bag to accept a builder class that defines a grammar for
    creating nodes with validation, schema constraints, and compilation.

    Attributes:
        node_class: Uses BuilderBagNode for builder-aware nodes.
        _builder: The BagBuilderBase instance attached to this bag.
    """

    node_class: type[BagNode] = BuilderBagNode

    @extract_kwargs(builder=True)
    def __init__(
        self,
        source: dict[str, Any] | None = None,
        builder: Any = None,
        builder_kwargs: dict | None = None,
    ):
        """Create a new BuilderBag.

        Args:
            source: Optional dict to initialize from.
            builder: Optional BagBuilderBase class for domain-specific
                node creation (e.g., HtmlBuilder for HTML generation).
            builder_kwargs: Extra kwargs passed to builder constructor.
                Can also be passed with builder_ prefix.
        """
        super().__init__(source=source)
        self._builder = builder(self, **builder_kwargs) if builder else None

    @property
    def builder(self) -> Any:
        """Get the builder associated with this Bag."""
        return self._builder

    @builder.setter
    def builder(self, value: Any) -> None:
        """Set the builder for this Bag."""
        self._builder = value

    def __getattribute__(self, name: str) -> Any:
        """Grammar-first attribute resolution.

        Resolution order:
        1. _prefix/dunder → normal (fast path)
        2. Infrastructure ('builder', 'node_class') → normal
        3. 'bag_' prefix → strip prefix, Bag method
        4. Builder set + name in schema → grammar tag (priority)
        5. Normal resolution (Bag methods, etc.)
        """
        if name.startswith("_"):
            return super().__getattribute__(name)

        if name in _BUILDERBAG_PROTECTED:
            return super().__getattribute__(name)

        if name.startswith("bag_"):
            return super().__getattribute__(name[4:])

        try:
            builder = super().__getattribute__("_builder")
        except AttributeError:
            builder = None
        if builder is not None and name in builder._schema_tag_names:
            return builder._bag_call(self, name)

        return super().__getattribute__(name)

    def __dir__(self) -> list[str]:
        """Schema elements, bag_ aliases for colliders, and base attributes."""
        base = set(super().__dir__())
        if self._builder is not None:
            schema_tags = self._builder._schema_tag_names
            for tag in schema_tags:
                base.add(tag)
                if tag in base:
                    base.add(f"bag_{tag}")
        return sorted(base)
