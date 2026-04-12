# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderBag and BuilderBagNode - Bag subclasses with builder support.

BuilderBag extends Bag to support domain-specific builders that define
grammars for creating nodes. BuilderBagNode extends BagNode to delegate
attribute access to the builder.

Example:
    >>> from genro_builders import BuilderBag
    >>> from genro_builders.contrib.html import HtmlBuilder
    >>> html = BuilderBag(builder=HtmlBuilder)
    >>> html.div(id='main').p(value='Hello')
"""
from __future__ import annotations

import inspect
from typing import Any

from genro_bag import Bag, BagNode
from genro_toolbox.decorators import extract_kwargs

from .pointer import is_pointer

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

    Properties for resolved access (read-only, always fresh):

        node.runtime_value  — node value with ^pointers resolved
        node.runtime_attrs  — attributes dict with ^pointers resolved
                              and callable attributes executed
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

    def abs_datapath(self, path: str) -> str:
        """Resolve any path form to an absolute datapath.

        Supports three forms:
            'user.name'         — absolute: returned as-is
            '.name'             — relative: resolved from this node's datapath
            '#address.street'   — symbolic: resolved via node_id lookup

        Args:
            path: The path to resolve.

        Returns:
            Absolute datapath string.

        Raises:
            KeyError: If a #node_id reference cannot be found.
        """
        if path.startswith("#"):
            return self._resolve_symbolic(path)
        if path.startswith("."):
            datapath = self._resolve_datapath()
            return f"{datapath}.{path[1:]}" if datapath else path[1:]
        return path

    def _resolve_symbolic(self, path: str) -> str:
        """Resolve a #node_id symbolic path to absolute.

        '#address.street' → find node_id 'address', get its datapath,
        append '.street'.
        """
        without_hash = path[1:]
        dot_pos = without_hash.find(".")
        if dot_pos >= 0:
            node_id = without_hash[:dot_pos]
            rest = without_hash[dot_pos + 1:]
        else:
            node_id = without_hash
            rest = ""

        builder = self._parent_bag._builder if self._parent_bag is not None else None
        if builder is None:
            raise KeyError(f"Cannot resolve symbolic path '{path}': no builder")

        target_node = builder.node_by_id(node_id)
        target_datapath = target_node.attr.get("datapath", "")

        if not target_datapath and hasattr(target_node, "_resolve_datapath"):
            target_datapath = target_node._resolve_datapath()

        if rest:
            return f"{target_datapath}.{rest}" if target_datapath else rest
        return target_datapath

    def _resolve_path(self, path: str) -> tuple[str, str | None]:
        """Parse and resolve a data path.

        Returns:
            Tuple of (resolved_path, attr_name_or_none).
        """
        attr_name = None
        if "?" in path:
            path, attr_name = path.split("?", 1)

        path = self.abs_datapath(path)

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

    # -------------------------------------------------------------------------
    # Value resolution (inspired by Genropy's currentFromDatasource pattern)
    # -------------------------------------------------------------------------

    def current_from_datasource(self, value: Any, data: Bag) -> Any:
        """Resolve a single value from this node's perspective.

        If value is a ^pointer string, resolves it against data using
        this node's datapath chain. Otherwise returns as-is.
        Callable values are NOT resolved here (see evaluate_on_node).

        Mirrors Genropy's ``currentFromDatasource`` on source nodes.
        """
        if is_pointer(value):
            return self._get_relative_data(data, value[1:])
        return value

    def get_attribute_from_datasource(self, attr_name: str, data: Bag) -> Any:
        """Resolve a single attribute value from the data store.

        Mirrors Genropy's ``getAttributeFromDatasource``.
        """
        value = self.attr.get(attr_name)
        if value is None:
            return None
        return self.current_from_datasource(value, data)

    def evaluate_on_node(self, data: Bag) -> dict[str, Any]:
        """Resolve all attributes and value in two passes.

        Pass 1: resolve ^pointer strings to values, skip callables.
        Pass 2: call each callable passing resolved attrs as kwargs
                (matched by parameter name).

        Returns dict with node_value, attrs, node.

        Mirrors Genropy's ``evaluateOnNode`` pattern where ``==`` formulas
        were evaluated with other attributes as locals.
        """
        raw_value = self.get_value(static=True)
        resolved_value = self.current_from_datasource(raw_value, data)

        # Pass 1: resolve non-callable attributes
        resolved: dict[str, Any] = {}
        callables: dict[str, Any] = {}
        for k, v in self.attr.items():
            if callable(v) and not isinstance(v, Bag):
                callables[k] = v
            else:
                resolved[k] = self.current_from_datasource(v, data)

        # Pass 2: execute callables with resolved attrs as context
        for k, func in callables.items():
            sig = inspect.signature(func)
            has_var_keyword = any(
                p.kind == inspect.Parameter.VAR_KEYWORD
                for p in sig.parameters.values()
            )
            if has_var_keyword:
                kwargs = {p: resolved[p] for p in resolved if not p.startswith("_")}
            else:
                kwargs: dict[str, Any] = {}
                for pname, param in sig.parameters.items():
                    if pname in resolved:
                        # Parameter matches a resolved attribute
                        kwargs[pname] = resolved[pname]
                    elif param.default is not inspect.Parameter.empty:
                        # Parameter has a default — resolve if pointer
                        kwargs[pname] = self.current_from_datasource(
                            param.default, data,
                        )
            resolved[k] = func(**kwargs)

        return {
            "node_value": resolved_value,
            "attrs": resolved,
            "node": self,
        }

    def _find_pipeline_builder(self) -> Any:
        """Walk parent chain to find the pipeline builder that owns data."""
        bag = self._parent_bag
        while bag is not None:
            pb = getattr(bag, "_pipeline_builder", None)
            if pb is not None:
                return pb
            parent_node = getattr(bag, "_parent_node", None)
            bag = getattr(parent_node, "_parent_bag", None) if parent_node else None
        return None

    @property
    def runtime_value(self) -> Any:
        """Node value with ^pointers resolved and callables executed."""
        builder = self._find_pipeline_builder()
        if builder is None:
            return self.get_value(static=True)
        return self.evaluate_on_node(builder.data)["node_value"]

    @property
    def runtime_attrs(self) -> dict[str, Any]:
        """Attributes with ^pointers resolved and callables executed.

        Excludes ``datapath`` which is a build-infrastructure attribute
        used for pointer resolution but not part of the element output.
        """
        builder = self._find_pipeline_builder()
        if builder is None:
            attrs = dict(self.attr)
        else:
            attrs = self.evaluate_on_node(builder.data)["attrs"]
        attrs.pop("datapath", None)
        return attrs


class BuilderBag(Bag):
    """Bag with builder support.

    Extends Bag to accept a builder class that defines a grammar for
    creating nodes with validation, schema constraints, and compilation.

    Attributes:
        node_class: Uses BuilderBagNode for builder-aware nodes.
        _builder: The BagBuilderBase instance attached to this bag.
    """

    node_class: type[BagNode] = BuilderBagNode
    _skip_parent_validation: bool = False

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


class Component(BuilderBag):
    """The internal bag passed to @component handlers.

    Semantically identical to BuilderBag. Exists as a named type
    so that component handler signatures read naturally::

        @component(sub_tags='')
        def login_form(self, comp: Component, **kwargs):
            comp.input(name='username')
    """
