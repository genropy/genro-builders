# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Build mixin: source-to-built materialization, pointer resolution,
binding registration, and source-change handlers (incremental compile).

Handles the complete build pipeline: ``build()`` walks the source Bag,
processes data elements, materializes normal elements into the built Bag,
registers pointer bindings, and resolves ^pointers just-in-time.
Source-change handlers (``_on_source_inserted/updated/deleted``) support
incremental updates after ``subscribe()``.

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
from genro_toolbox.smarttimer import cancel_timer, set_interval

from ..builder_bag import BuilderBag
from ..pointer import is_pointer, parse_pointer, scan_for_pointers

if TYPE_CHECKING:
    from genro_bag import BagNode


class _BuildMixin:
    """Mixin for build walk, pointer resolution, bindings, and source changes."""

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
        binding: Any,
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
            binding: BindingManager for subscription registration.
            prefix: Path prefix for subscription map keys.
        """
        # Ensure built nodes can find this builder for runtime_attrs
        if not hasattr(target, "_pipeline_builder") or target._pipeline_builder is None:
            target._pipeline_builder = self

        # Pass 1: process data_element nodes
        for node in source:
            if node.attr.get("_is_data_element"):
                self._process_infra_node(node, data)

        # Pass 2: materialize normal nodes
        nodes = [n for n in source if not n.attr.get("_is_data_element")]
        return self._build_walk_nodes(nodes, 0, target, data, binding, prefix)

    def _build_walk_nodes(
        self,
        nodes: list,
        idx: int,
        target: Bag,
        data: Bag,
        binding: Any,
        prefix: str,
    ) -> Any:
        """Process nodes[idx:] into target. Returns None or coroutine."""
        while idx < len(nodes):
            node = nodes[idx]
            built_path = f"{prefix}.{node.label}" if prefix else node.label
            binding.unbind_path(built_path)

            iterate_raw = node.attr.get("iterate")
            if iterate_raw and is_pointer(iterate_raw) and node.resolver is not None:
                self._materialize_iterate(
                    node, iterate_raw, target, data, binding, built_path,
                )
                idx += 1
                continue

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
                    self._materialize_node(node, resolved, target, data, binding, built_path)
                    if isinstance(resolved, Bag):
                        child_result = self._build_walk(
                            resolved, target.get_node(node.label).value,
                            data, binding, prefix=built_path,
                        )
                        await smartawait(child_result)
                    # Process remaining nodes
                    rest = self._build_walk_nodes(
                        remaining_nodes, remaining_idx + 1, target, data, binding, prefix,
                    )
                    await smartawait(rest)

                return cont()

            self._materialize_node(node, value, target, data, binding, built_path)
            if isinstance(value, Bag):
                child_result = self._build_walk(value, target.get_node(node.label).value, data, binding, prefix=built_path)
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
                            remaining_nodes, remaining_idx, target, data, binding, prefix,
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
        binding: Any,
        built_path: str,
    ) -> None:
        """Materialize a single node into the target bag."""
        new_node = target.set_item(
            node.label,
            value if not isinstance(value, Bag) else BuilderBag(builder=type(self)),
            _attributes=dict(node.attr),
            node_tag=node.node_tag,
        )
        self._register_bindings(new_node, built_path, data, binding)

    def _materialize_iterate(
        self,
        node: BagNode,
        iterate_raw: str,
        target: Bag,
        data: Bag,
        binding: Any,
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
        container_bag = BuilderBag(builder=type(self))
        container_attrs = {k: v for k, v in node.attr.items() if k != "iterate"}
        container_node = target.set_item(
            node.label,
            container_bag,
            _attributes=container_attrs,
            node_tag=node.node_tag,
        )
        self._register_bindings(container_node, built_path, data, binding)

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
                BuilderBag(builder=type(self)),
                _attributes={"datapath": child_path},
            )
            self._register_bindings(child_node, child_built_path, data, binding)
            self._build_walk(
                value, child_node.value, data, binding, prefix=child_built_path,
            )

    def _process_infra_node(self, node: BagNode, data: Bag) -> None:
        """Process a data_element node during build walk.

        Resolves ^pointers in attributes, then executes the appropriate
        action: data_setter writes value, data_formula computes, data_controller executes.
        Registers formula/controller with ^pointer deps for reactivity.
        Injects _node into callable kwargs if the callable accepts it.
        """
        attrs = dict(node.attr)
        path = attrs.pop("_data_path", None)
        attrs.pop("_is_data_element", None)

        # Resolve relative path
        if path is not None and path.startswith(".") and hasattr(node, "abs_datapath"):
            path = node.abs_datapath(path)

        # Keep raw attrs (with ^pointers) for reactivity registration
        raw_attrs = {k: v for k, v in attrs.items() if not k.startswith("_")}
        resolved = self._resolve_infra_kwargs(attrs, node, data)

        tag = node.node_tag
        if tag == "data_setter":
            value = resolved.get("value")
            if isinstance(value, dict):
                value = Bag(source=value)
            if path is not None:
                data.set_item(path, value)
        elif tag == "data_formula":
            func = resolved.pop("func", None)
            if func is not None and path is not None:
                result = self._call_with_node(func, node, resolved)
                if isinstance(result, dict):
                    result = Bag(source=result)
                data.set_item(path, result)
        elif tag == "data_controller":
            func = resolved.pop("func", None)
            if func is not None:
                self._call_with_node(func, node, resolved)

        # Register formula/controller with pointer deps for reactivity
        if tag in ("data_formula", "data_controller"):
            delay = attrs.get("_delay")
            interval = attrs.get("_interval")
            has_pointer_deps = any(is_pointer(v) for v in raw_attrs.values())
            if has_pointer_deps or interval is not None:
                self._formula_registry[node.label] = {
                    "node": node,
                    "tag": tag,
                    "path": path,
                    "raw_attrs": raw_attrs,
                    "_delay": delay,
                    "_interval": interval,
                }

        # Collect _onBuilt hooks
        on_built = attrs.get("_onBuilt")
        if callable(on_built):
            self._infra_on_built_hooks.append(on_built)

    def _call_with_node(
        self, func: Any, node: BagNode, resolved: dict[str, Any],
    ) -> Any:
        """Call func with resolved kwargs, injecting _node if accepted."""
        sig = inspect.signature(func)
        if "_node" in sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        ):
            resolved["_node"] = node
        return func(**resolved)

    def _resolve_infra_kwargs(
        self, attrs: dict[str, Any], node: BagNode, data: Bag,
    ) -> dict[str, Any]:
        """Resolve ^pointer values in data element attributes."""
        resolved: dict[str, Any] = {}
        for k, v in attrs.items():
            if k.startswith("_"):
                continue
            resolved[k] = node.current_from_datasource(v, data)
        return resolved

    # -----------------------------------------------------------------------
    # Pointer resolution
    # -----------------------------------------------------------------------

    def _register_bindings(
        self, node: BagNode, built_path: str, data: Bag, binding: Any,
    ) -> None:
        """Register ^pointer subscriptions without resolving values.

        The built node keeps the ^pointer string intact. Resolution happens
        just-in-time during render/compile via _resolve_node.

        Also registers dependencies from computed attributes (callables
        with ^pointer defaults in their parameters).
        """
        pointers = scan_for_pointers(node)

        # Scan callable attributes for ^pointer defaults
        for attr_name, attr_value in node.attr.items():
            if attr_name.startswith("_") or not callable(attr_value):
                continue
            for pointer_raw in self._extract_pointer_defaults(attr_value):
                pointer_info = parse_pointer(pointer_raw)
                pointers.append((pointer_info, f"attr:{attr_name}"))

        if not pointers:
            return

        for pointer_info, location in pointers:
            data_path, attr_name = node._resolve_path(pointer_info.raw[1:])
            data_key = f"{data_path}?{attr_name}" if attr_name else data_path
            built_entry = built_path if location == "value" else f"{built_path}?{location[5:]}"

            binding.register(data_key, built_entry)

    def _extract_pointer_defaults(self, func: Any) -> list[str]:
        """Extract ^pointer strings from callable parameter defaults."""
        result: list[str] = []
        sig = inspect.signature(func)
        for param in sig.parameters.values():
            if param.default is not inspect.Parameter.empty and is_pointer(param.default):
                result.append(param.default)
        return result

    def _resolve_node(self, node: BagNode, data: Bag) -> dict[str, Any]:
        """Produce a resolved view of a built node.

        Delegates to node.evaluate_on_node(data) which resolves ^pointer
        strings, callables with ^pointer defaults, and plain values.
        The built node is NOT modified.

        Used by node.runtime_attrs/runtime_value for just-in-time resolution.
        """
        if hasattr(node, "evaluate_on_node"):
            return node.evaluate_on_node(data)

        # Fallback for plain BagNode (no builder)
        return {
            "node_value": node.get_value(static=True),
            "attrs": dict(node.attr),
            "node": node,
        }

    # -----------------------------------------------------------------------
    # Build / subscribe / rebuild
    # -----------------------------------------------------------------------

    def build(self) -> Any:
        """Materialize source -> built.

        Two-pass walk: data_elements first, then normal elements.
        After walk, sorts formula by dependency order and calls _onBuilt hooks.
        Does NOT activate reactivity -- call ``subscribe()`` separately.

        Returns None in sync context, or a coroutine in async context.
        In async context, caller must: ``await smartawait(builder.build())``.
        """
        self._clear_built()
        self._formula_registry = {}
        self._formula_order: list[str] = []
        self._infra_on_built_hooks: list[Any] = []

        walk_result = self._build_walk(
            self.source, self.built, self.data, self._binding,
        )

        def finalize(_: Any) -> None:
            self._formula_order = self._topological_sort_formulas()
            for hook in self._infra_on_built_hooks:
                hook(self)
            self._infra_on_built_hooks = []

        return smartcontinuation(walk_result, finalize)

    def subscribe(self) -> None:
        """Activate reactive bindings on the built Bag.

        After this call, changes to data are propagated to built nodes
        and output is re-rendered automatically. Formula/controller with
        ^pointer dependencies are re-executed when their sources change.
        Call after ``build()``.
        """
        self._binding.subscribe(self.built, self.data)

        self.source.subscribe(
            "source_watcher",
            delete=self._on_source_deleted,
            insert=self._on_source_inserted,
            update=self._on_source_updated,
        )

        if self._formula_registry:
            self.data.subscribe(
                "formula_watcher",
                any=self._on_formula_data_changed,
            )

        # Start interval timers for formula/controller with _interval
        for entry_id, entry in self._formula_registry.items():
            interval = entry.get("_interval")
            if interval is not None:
                timer_id = set_interval(
                    interval,
                    self._on_interval_tick,
                    entry_id,
                )
                self._active_timers[f"interval:{entry_id}"] = timer_id

        self._auto_compile = True
        self._rerender()

    def rebuild(self, main: Any = None) -> None:
        """Full rebuild: clear source, optionally re-populate, build.

        Args:
            main: Optional callable(source) to populate the source bag.
                If not provided, only clears and rebuilds from current source.
        """
        self.source.unsubscribe("source_watcher", any=True)
        self._auto_compile = False
        self._clear_source()
        if main is not None:
            main(self.source)
        self.build()

    def _clear_built(self) -> None:
        """Clear the built bag without destroying the shell."""
        self._binding.unbind()
        if self._data is not None:
            self._data.unsubscribe("formula_watcher", any=True)
        for timer_id in self._active_timers.values():
            cancel_timer(timer_id)
        self._active_timers = {}
        self._formula_registry = {}
        self.built.clear()

    def _clear_source(self) -> None:
        """Clear the source bag and the node_id map."""
        self._node_id_map.clear()
        new_root = BuilderBag(builder=type(self))
        self._source_shell.set_item("root", new_root)
        self._bag = self.source

    def node_by_id(self, node_id: str) -> BagNode:
        """Retrieve a node by its unique node_id.

        Searches this builder's map first, then the source builder's map
        (in standalone mode, the source Bag has its own builder instance).

        Args:
            node_id: The unique identifier assigned via node_id= attribute.

        Returns:
            The BagNode with the given node_id.

        Raises:
            KeyError: If no node with the given node_id exists.
        """
        if node_id in self._node_id_map:
            return self._node_id_map[node_id]
        # In standalone mode, source has its own builder with its own map
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
    # Source change handlers (incremental compile)
    # -----------------------------------------------------------------------

    def _on_source_deleted(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        ind: int | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node is deleted from the source."""
        if not self._auto_compile or node is None:
            return
        # Data elements were never materialized in built
        if node.attr.get("_is_data_element"):
            return
        parts = [str(p) for p in pathlist] if pathlist else []
        parts.append(node.label)
        path = ".".join(parts)
        self._binding.unbind_path(path)
        self.built.del_item(path, _reason="source")
        self._rerender()

    def _on_source_inserted(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        ind: int | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> Any:
        """Called when a node is inserted into the source."""
        if not self._auto_compile or node is None:
            return None

        # Data element: process as infra and re-render
        if node.attr.get("_is_data_element"):
            self._process_infra_node(node, self.data)
            self._rerender()
            return None

        parent_path = ".".join(str(p) for p in pathlist) if pathlist else ""

        if parent_path:
            target_bag = self.built.get_item(parent_path)
            if not isinstance(target_bag, Bag):
                return None
        else:
            target_bag = self.built

        node_path = f"{parent_path}.{node.label}" if parent_path else node.label

        value = node.get_value(static=False) if node.resolver is not None else node.static_value

        if self._is_coroutine(value):
            async def cont_inserted(value=value):
                resolved = await value
                self._materialize_inserted(
                    node, resolved, target_bag, node_path, ind,
                )
                self._rerender()

            return cont_inserted()

        self._materialize_inserted(node, value, target_bag, node_path, ind)
        self._rerender()
        return None

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
            value if not isinstance(value, Bag) else BuilderBag(builder=type(self)),
            _attributes=dict(node.attr),
            node_tag=node.node_tag,
            node_position=ind,
            _reason="source",
        )

        self._register_bindings(
            new_node, node_path, self.data, self._binding,
        )

        if isinstance(value, Bag):
            self._build_walk(
                value, new_node.value, self.data, self._binding, prefix=node_path,
            )

    def _materialize_updated(
        self,
        built_node: BagNode,
        value: Any,
        path: str,
    ) -> None:
        """Materialize an updated value into the built node."""
        if isinstance(value, Bag):
            built_node.set_value(BuilderBag(builder=type(self)), _reason="source")
            self._register_bindings(
                built_node, path, self.data, self._binding,
            )
            self._build_walk(
                value, built_node.value, self.data, self._binding, prefix=path,
            )
        else:
            built_node.set_value(value, _reason="source")
            self._register_bindings(
                built_node, path, self.data, self._binding,
            )

    def _on_source_updated(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> Any:
        """Called when a node in the source is updated (value or attributes)."""
        if not self._auto_compile or pathlist is None:
            return None

        # Data element: re-process and re-render
        if node is not None and node.attr.get("_is_data_element"):
            self._process_infra_node(node, self.data)
            self._rerender()
            return None

        path = ".".join(str(p) for p in pathlist)
        built_node = self.built.get_node(path)
        if built_node is None:
            return None

        if evt == "upd_value":
            value = node.get_value(static=False) if node.resolver is not None else node.static_value

            self._binding.unbind_path(path)

            if self._is_coroutine(value):
                async def cont_updated(value=value):
                    resolved = await value
                    self._materialize_updated(built_node, resolved, path)
                    self._rerender()

                return cont_updated()

            self._materialize_updated(built_node, value, path)

        elif evt == "upd_attrs":
            if node is not None:
                built_node.set_attr(dict(node.attr))
                self._binding.unbind_path(path)
                self._register_bindings(
                    built_node, path, self.data, self._binding,
                )

        self._rerender()
