# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuiltBag and BuiltBagNode — execution-focused Bag for the built tree.

The built Bag is the output of the build phase. It is completely
self-sufficient: renderer, compiler, and reactive dispatch consume
it without any reference to source, grammar, or builder.

BuiltBagNode provides:
    - data — direct reference to the data Bag (set at build time)
    - runtime_value / runtime_attrs — resolved attributes for render/compile
    - execute_func() — execute a data provider function (data_controller)
    - current_from_datasource() — resolve ^pointer to value

BuiltBag provides:
    - Uses BuiltBagNode as node class
    - Pure container, no builder/grammar knowledge
"""
from __future__ import annotations

import inspect
from typing import Any

from genro_bag import Bag, BagNode

from .builder._binding import is_pointer


class BuiltBagNode(BagNode):
    """Node in the built tree. Resolves pointers, executes functions, writes data.

    Each node holds a direct reference to the data Bag (_data),
    set during materialization. No parent chain traversal needed.

    Inherits from BagNode (not BuilderBagNode): no grammar delegation,
    no schema awareness, no __getattr__ magic. Pure execution.
    """

    _data: Bag | None = None
    _builder_name: str | None = None

    @property
    def data(self) -> Bag:
        """Direct access to the data Bag — O(1)."""
        if self._data is not None:
            return self._data
        return Bag()

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

    def abs_datapath(self, path: str) -> str:
        """Resolve any path form to an absolute datapath in the global store.

        Supports volume syntax (``volume:local_path``) and two local forms:
            'field'      — local to current builder
            '.field'     — relative: resolved from this node's datapath

        In managed context (node has ``_builder_name``), the builder name
        is prepended. In standalone context, the path is returned as-is.
        """
        builder_name = self._builder_name

        # Handle volume syntax: "other_builder:local_path"
        volume = None
        if ":" in path and not path.startswith("."):
            volume, path = path.split(":", 1)

        if path.startswith("."):
            datapath = self._resolve_datapath()
            if not datapath:
                resolved = path[1:] if path[1:] else ""
            else:
                resolved = f"{datapath}.{path[1:]}" if path[1:] else datapath
            # Relative paths resolved via datapath chain may already include
            # the builder name (e.g. iterate sets absolute datapaths).
            # If so, skip prepending to avoid double-prefix.
            prefix = volume if volume is not None else builder_name
            if prefix and resolved.startswith(f"{prefix}."):
                return resolved
            if prefix is not None:
                return f"{prefix}.{resolved}" if resolved else prefix
            return resolved

        resolved = path

        # Prepend volume or builder name
        prefix = volume if volume is not None else builder_name
        if prefix is not None:
            return f"{prefix}.{resolved}" if resolved else prefix
        return resolved

    def get_relative_data(self, path: str) -> Any:
        """Read a value from the data Bag, resolving relative paths.

        Args:
            path: Data path. Syntax:
                'alfa.beta'       — absolute
                '.beta'           — relative to this node's datapath
                'alfa.beta?color' — attribute 'color' of node 'alfa.beta'
        """
        attr_name = None
        if "?" in path:
            path, attr_name = path.split("?", 1)
        resolved = self.abs_datapath(path)
        if attr_name is not None:
            node = self.data.get_node(resolved)
            return node.attr.get(attr_name) if node is not None else None
        return self.data.get_item(resolved)

    def set_relative_data(self, path: str, value: Any) -> None:
        """Write a value to the data Bag, resolving relative paths.

        Anti-loop: _reason=self is automatic.

        Args:
            path: Data path (same syntax as get_relative_data).
            value: The value to set.
        """
        attr_name = None
        if "?" in path:
            path, attr_name = path.split("?", 1)
        resolved = self.abs_datapath(path)
        if attr_name is not None:
            self.data.set_attr(resolved, **{attr_name: value})
        else:
            self.data.set_item(resolved, value, _reason=self)

    def current_from_datasource(self, value: Any) -> Any:
        """Resolve a single value: if ^pointer, read from data; else return as-is."""
        if is_pointer(value):
            return self.get_relative_data(value[1:])
        return value

    def evaluate_on_node(self) -> dict[str, Any]:
        """Resolve all attributes and value in two passes.

        Pass 1: resolve ^pointer strings to values, skip callables.
        Pass 2: call each callable passing resolved attrs as kwargs.

        Returns dict with node_value, attrs, node.
        """
        raw_value = self.get_value(static=True)
        resolved_value = self.current_from_datasource(raw_value)

        # Pass 1: resolve non-callable attributes
        resolved: dict[str, Any] = {}
        callables: dict[str, Any] = {}
        for k, v in self.attr.items():
            if callable(v) and not isinstance(v, Bag):
                callables[k] = v
            else:
                resolved[k] = self.current_from_datasource(v)

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
                        kwargs[pname] = resolved[pname]
                    elif param.default is not inspect.Parameter.empty:
                        kwargs[pname] = self.current_from_datasource(
                            param.default,
                        )
            resolved[k] = func(**kwargs)

        return {
            "node_value": resolved_value,
            "attrs": resolved,
            "node": self,
        }

    @property
    def runtime_value(self) -> Any:
        """Node value with ^pointers resolved and callables executed."""
        return self.evaluate_on_node()["node_value"]

    @property
    def runtime_attrs(self) -> dict[str, Any]:
        """Attributes with ^pointers resolved, callables executed, datapath excluded."""
        attrs = self.evaluate_on_node()["attrs"]
        attrs.pop("datapath", None)
        return attrs



class BuiltBag(Bag):
    """Bag for the built tree. Pure container, no builder/grammar knowledge."""

    node_class: type[BagNode] = BuiltBagNode
