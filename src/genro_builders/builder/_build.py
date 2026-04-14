# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Build mixin: source-to-built materialization.

Handles the build pipeline: ``build()`` walks the source Bag,
processes data elements, and materializes normal elements into the
built Bag. Incremental compile (source-change handlers) lives in
``_reactivity.ReactivityEngine``.

Async-safe: when called inside an async context (running event loop),
``build()`` and the incremental handlers return coroutines instead of
None.  Component resolvers that return coroutines from
``get_value(static=False)`` are awaited transparently via the
continuation pattern (same as ``_htraverse`` in genro-bag).

Sync usage (unchanged)::

    builder.build()

Async usage::

    from genro_toolbox import smartawait
    await smartawait(builder.build())
"""

from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any

from genro_bag import Bag
from genro_toolbox import smartawait, smartcontinuation

from ..builder_bag import BuilderBag
from ..built_bag import BuiltBag
from ._binding import is_pointer, parse_pointer

if TYPE_CHECKING:
    from genro_bag import BagNode


class _BuildMixin:
    """Mixin for build walk and materialization."""

    # -----------------------------------------------------------------------
    # Async context detection
    # -----------------------------------------------------------------------

    @property
    def in_async_context(self) -> bool:
        """Whether we are currently running inside an async context."""
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    def _is_coroutine(self, value: Any) -> bool:
        """Check if value is a coroutine (only possible in async context)."""
        return self.in_async_context and asyncio.iscoroutine(value)

    # -----------------------------------------------------------------------
    # Build walk (source -> built materialization)
    # -----------------------------------------------------------------------

    def _build_walk(
        self,
        source: Bag,
        target: Bag,
        data: Bag,
        prefix: str = "",
    ) -> Any:
        """Recursive walk: two-pass processing.

        Pass 1: Process data_element nodes (side effects on data Bag).
        Pass 2: Materialize normal elements and components in built.

        Returns None in sync context, or a coroutine in async context
        (when a resolver returns a coroutine from get_value).

        Args:
            source: The source Bag to compile from.
            target: The built Bag to populate.
            data: Data Bag for ^pointer resolution.
            prefix: Path prefix for built node paths.
        """
        # Pass 1: execute data_element nodes (populate data store)
        for node in source:
            if node.attr.get("_is_data_element"):
                self._process_infra_node(node, data)

        # Pass 2: materialize ALL nodes into built
        nodes = list(source)
        return self._build_walk_nodes(nodes, 0, target, data, prefix)

    def _build_walk_nodes(
        self,
        nodes: list,
        idx: int,
        target: Bag,
        data: Bag,
        prefix: str,
    ) -> Any:
        """Process nodes[idx:] into target. Returns None or coroutine."""
        while idx < len(nodes):
            node = nodes[idx]
            built_path = f"{prefix}.{node.label}" if prefix else node.label

            iterate_raw = node.attr.get("iterate")
            if iterate_raw and is_pointer(iterate_raw) and node.resolver is not None:
                self._materialize_iterate(
                    node, iterate_raw, target, data, built_path,
                )
                idx += 1
                continue

            if node.attr.get("_is_data_element"):
                value = node.static_value
            else:
                value = node.get_value(static=False) if node.resolver is not None else node.static_value

            if self._is_coroutine(value):
                remaining_idx = idx
                remaining_nodes = nodes

                async def cont(
                    value=value,
                    node=node,
                    built_path=built_path,
                    remaining_nodes=remaining_nodes,
                    remaining_idx=remaining_idx,
                ):
                    resolved = await value
                    self._materialize_node(node, resolved, target, data, built_path)
                    if isinstance(resolved, Bag):
                        child_result = self._build_walk(
                            resolved, target.get_node(node.label).value,
                            data, prefix=built_path,
                        )
                        await smartawait(child_result)
                    # Process remaining nodes
                    rest = self._build_walk_nodes(
                        remaining_nodes, remaining_idx + 1, target, data, prefix,
                    )
                    await smartawait(rest)

                return cont()

            self._materialize_node(node, value, target, data, built_path)
            if isinstance(value, Bag):
                child_result = self._build_walk(value, target.get_node(node.label).value, data, prefix=built_path)
                if self._is_coroutine(child_result):
                    remaining_idx = idx + 1
                    remaining_nodes = nodes

                    async def cont_child(
                        child_result=child_result,
                        remaining_nodes=remaining_nodes,
                        remaining_idx=remaining_idx,
                    ):
                        await child_result
                        rest = self._build_walk_nodes(
                            remaining_nodes, remaining_idx, target, data, prefix,
                        )
                        await smartawait(rest)

                    return cont_child()

            idx += 1

        return None

    def _materialize_node(
        self,
        node: BagNode,
        value: Any,
        target: Bag,
        data: Bag,
        built_path: str,
    ) -> None:
        """Materialize a single node into the target bag."""
        new_node = target.set_item(
            node.label,
            value if not isinstance(value, Bag) else BuiltBag(),
            _attributes=dict(node.attr),
            node_tag=node.node_tag,
        )
        new_node._data = data

    def _materialize_iterate(
        self,
        node: BagNode,
        iterate_raw: str,
        target: Bag,
        data: Bag,
        built_path: str,
    ) -> None:
        """Materialize a component N times, once per child in the iterated bag.

        Creates a container node in built, then for each child of the data bag
        pointed to by iterate_raw, expands the component with datapath set to
        the child's path.
        """
        pointer_info = parse_pointer(iterate_raw)
        data_path = pointer_info.path

        data_bag = data.get_item(data_path)

        # Create container node in built (strip iterate — consumed here)
        container_bag = BuiltBag()
        container_attrs = {k: v for k, v in node.attr.items() if k != "iterate"}
        container_node = target.set_item(
            node.label,
            container_bag,
            _attributes=container_attrs,
            node_tag=node.node_tag,
        )
        container_node._data = data

        if not isinstance(data_bag, Bag):
            return

        for child_data_node in data_bag:
            child_path = f"{data_path}.{child_data_node.label}"
            # Expand the component for this child
            value = node.get_value(static=False)
            if not isinstance(value, Bag):
                continue

            child_built_path = f"{built_path}.{child_data_node.label}"
            child_node = container_bag.set_item(
                child_data_node.label,
                BuiltBag(),
                _attributes={"datapath": child_path},
            )
            child_node._data = data
            self._build_walk(
                value, child_node.value, data, prefix=child_built_path,
            )

    def _process_infra_node(self, node: BagNode, data: Bag) -> None:
        """Execute a data_element node at build time.

        Resolves ^pointers, executes the appropriate action to populate
        the data store. The node will then be materialized in the built
        bag like any other node.
        """
        attrs = dict(node.attr)
        path = attrs.get("_data_path")

        # Resolve relative path to absolute
        if path is not None and path.startswith(".") and hasattr(node, "abs_datapath"):
            abs_path = node.abs_datapath(path)
            node.attr["_data_path"] = abs_path
            path = abs_path

        raw_attrs = {k: v for k, v in attrs.items() if not k.startswith("_")}

        tag = node.node_tag
        if tag == "data_setter":
            value = node.current_from_datasource(attrs.get("value"), data)
            if isinstance(value, dict):
                value = Bag(source=value)
            if path is not None:
                data.set_item(path, value)
        elif tag in ("data_formula", "data_controller"):
            func = raw_attrs.get("func")
            if "_accepts_node" not in node.attr:
                sig = inspect.signature(func)
                node.attr["_accepts_node"] = (
                    "_node" in sig.parameters
                    or any(p.kind == inspect.Parameter.VAR_KEYWORD
                           for p in sig.parameters.values())
                )
            result = node.execute_func(attrs, data)
            if tag == "data_formula":
                if isinstance(result, dict):
                    result = Bag(source=result)
                data.set_item(path, result)

        # Collect _onBuilt hooks
        on_built = attrs.get("_onBuilt")
        if callable(on_built):
            self._infra_on_built_hooks.append(on_built)

    # -----------------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------------

    def _ensure_reactivity(self) -> Any:
        """Ensure ReactivityEngine exists (created lazily)."""
        if self._reactivity is None:
            from ._reactivity import ReactivityEngine
            self._reactivity = ReactivityEngine(self)
        return self._reactivity

    def build(self) -> Any:
        """Materialize source -> built.

        Two-pass walk: execute data_elements first (populate data store),
        then materialize ALL nodes into the built bag.
        Does NOT activate reactivity -- call ``subscribe()`` separately.

        Returns None in sync context, or a coroutine in async context.
        """
        self._ensure_reactivity()
        self._clear_built()
        self._infra_on_built_hooks: list[Any] = []

        walk_result = self._build_walk(
            self.source, self.built, self.data,
        )

        def finalize(_: Any) -> None:
            for hook in self._infra_on_built_hooks:
                hook(self)
            self._infra_on_built_hooks = []

        return smartcontinuation(walk_result, finalize)

    def _clear_built(self) -> None:
        """Clear the built bag without destroying the shell."""
        r = self._reactivity
        if r is not None:
            r.clear()
        self.built.clear()

    def _clear_source(self) -> None:
        """Clear the source bag and the node_id map."""
        self._node_id_map.clear()
        new_root = BuilderBag(builder=type(self))
        self._source_shell.set_item("root", new_root)
        self._bag = self.source

    def node_by_id(self, node_id: str) -> BagNode:
        """Retrieve a node by its unique node_id."""
        if node_id in self._node_id_map:
            return self._node_id_map[node_id]
        if hasattr(self, "_source_shell"):
            source_builder = self.source._builder
            if source_builder is not None and source_builder is not self and node_id in source_builder._node_id_map:  # noqa: SIM102
                return source_builder._node_id_map[node_id]
        raise KeyError(f"No node with node_id '{node_id}'") from None

    def _get_output(self, kind: str, registry: dict[str, Any], name: str | None) -> Any:
        """Resolve a named or single output instance from a registry."""
        if not registry:
            return None
        if name is None:
            if len(registry) == 1:
                return next(iter(registry.values()))
            raise RuntimeError(f"Multiple {kind}s registered, specify name")
        if name not in registry:
            raise KeyError(f"{kind} '{name}' not found")
        return registry[name]

    # -----------------------------------------------------------------------
    # Materialization helpers (used by ReactivityEngine for incremental)
    # -----------------------------------------------------------------------

    def _materialize_inserted(
        self,
        node: BagNode,
        value: Any,
        target_bag: Bag,
        node_path: str,
        ind: int | None,
    ) -> None:
        """Materialize an inserted source node into the built bag."""
        new_node = target_bag.set_item(
            node.label,
            value if not isinstance(value, Bag) else BuiltBag(),
            _attributes=dict(node.attr),
            node_tag=node.node_tag,
            node_position=ind,
            _reason="source",
        )
        new_node._data = self.data

        if isinstance(value, Bag):
            self._build_walk(
                value, new_node.value, self.data, prefix=node_path,
            )

    def _materialize_updated(
        self,
        built_node: BagNode,
        value: Any,
        path: str,
    ) -> None:
        """Materialize an updated value into the built node."""
        if isinstance(value, Bag):
            built_node.set_value(BuiltBag(), _reason="source")
            self._build_walk(
                value, built_node.value, self.data, prefix=path,
            )
        else:
            built_node.set_value(value, _reason="source")
