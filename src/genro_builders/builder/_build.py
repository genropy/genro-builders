# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Build mixin: source-to-built materialization.

Handles the build pipeline: ``build()`` walks the source Bag,
processes data elements, and materializes normal elements into the
built Bag. Incremental compile (source-change handlers) lives in
``_reactivity.ReactivityEngine``.

Async-safe by delegation: every value flowing through the walk comes
from ``node.get_value()`` and is passed through ``smartcontinuation``,
which transparently handles both concrete values (sync path) and
coroutines (async continuation). The walk itself has no knowledge of
asyncio — the async/sync decision is absorbed by the resolver layer
and by ``smartcontinuation``.

Sync usage::

    builder.build()

Async usage::

    from genro_toolbox import smartawait
    await smartawait(builder.build())
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode
from genro_toolbox import smartcontinuation

from ..builder_bag import BuilderBag, Component
from ..built_bag import BuiltBag
from ..formula_resolver import FormulaResolver
from ._binding import is_pointer, parse_pointer, scan_for_pointers


class _BuildMixin:
    """Mixin for build walk and materialization."""

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
        """Recursive walk: materialize source into built.

        Data elements (data_setter, data_formula) are accumulated in
        _pending_data_elements for deferred processing — they need the
        built tree to be complete so that abs_datapath can resolve
        relative paths via the ancestor chain.

        Elements are materialized directly. Components are expanded
        (transparent macro) and their content is processed recursively
        into the same target. Components with iterate expand N times,
        once per data child.

        Returns None in sync context, or a coroutine in async context.
        """
        # Accumulate data elements with their built parent for deferred processing
        built_parent = target.parent_node
        for node in source:
            if node.node_tag in ("data_setter", "data_formula"):
                self._pending_data_elements.append((node, built_parent))
                continue

        nodes = [
            n for n in source
            if n.node_tag not in ("data_setter", "data_formula")
        ]
        return self._build_walk_nodes(nodes, 0, target, data, prefix)

    def _build_walk_nodes(
        self,
        nodes: list,
        idx: int,
        target: Bag,
        data: Bag,
        prefix: str,
    ) -> Any:
        """Process nodes[idx:] into target.

        Returns None in sync path, or a coroutine when any resolver in
        the walk produced an awaitable. ``smartcontinuation`` folds the
        two cases into a single code path.
        """
        while idx < len(nodes):
            node = nodes[idx]
            built_path = f"{prefix}.{node.label}" if prefix else node.label

            # --- Component with iterate: expand N times ---
            iterate_raw = node.attr.get("iterate")
            if iterate_raw and is_pointer(iterate_raw) and node.attr.get("_is_component"):
                self._expand_component_iterate(
                    node, iterate_raw, target, data, built_path,
                )
                idx += 1
                continue

            # --- Component without iterate: expand once (transparent macro) ---
            if node.attr.get("_is_component"):
                proxy = node.value
                comp_bag = self._expand_component(proxy)
                if isinstance(comp_bag, Bag):
                    walk = self._build_walk(comp_bag, target, data, prefix)
                    next_idx = idx + 1

                    def after_walk(_: Any, next_idx: int = next_idx) -> Any:
                        return self._build_walk_nodes(nodes, next_idx, target, data, prefix)

                    return smartcontinuation(walk, after_walk)
                idx += 1
                continue

            # --- Element: materialize and recurse on children ---
            value = node.get_value()

            def after_element(
                resolved: Any,
                node: BagNode = node,
                built_path: str = built_path,
                next_idx: int = idx + 1,
            ) -> Any:
                new_node = self._materialize_node(node, resolved, target, data, built_path)
                if isinstance(resolved, Bag):
                    child_result = self._build_walk(
                        resolved, new_node.value, data, prefix=built_path,
                    )

                    def after_child(_: Any, next_idx: int = next_idx) -> Any:
                        return self._build_walk_nodes(nodes, next_idx, target, data, prefix)

                    return smartcontinuation(child_result, after_child)
                return self._build_walk_nodes(nodes, next_idx, target, data, prefix)

            return smartcontinuation(value, after_element)

        return None

    def _materialize_node(
        self,
        node: BagNode,
        value: Any,
        target: Bag,
        data: Bag,
        built_path: str,
    ) -> BagNode:
        """Materialize a single element node into the target bag.

        Uses ``_child`` (grammar) so that labels are auto-generated in
        the target — transparent components calling the same element
        multiple times produce unique labels (no collision).

        Returns the newly created node.
        """
        attrs = dict(node.attr)
        attrs.pop("node_id", None)  # node_id is not a build-time attr
        return self._child(
            target,
            node.node_tag,
            node_value=value if not isinstance(value, Bag) else BuiltBag(),
            **attrs,
        )

    def _expand_component(self, proxy: Any, **framework_kwargs: Any) -> Bag:
        """Execute a component handler, returning the populated Bag.

        Handler receives ``main_kwargs=dict`` produced by merging:
          * user main kwargs (from call-time ``main_*`` / ``main_kwargs={...}``,
            stored on the proxy as ``_user_main_kwargs``);
          * framework main kwargs (e.g. ``main_datapath`` injected by iterate).

        On key collision the framework value wins, **except** for
        ``datapath`` where the two are concatenated as
        ``f"{user_datapath}{framework_datapath}"`` (the framework already
        emits the leading dot, so the result is ``"<user>.<row>"``). See
        contract §2bis.8 / §8.3.

        The expanded bag must be a tree (exactly one top-level node); if
        ``main_tag`` is declared in the schema, the top-level node_tag
        must match. Both invariants are validated here.
        """
        builder = object.__getattribute__(proxy, "_builder")
        comp_name = object.__getattribute__(proxy, "_component_name")
        user_main_kwargs = object.__getattribute__(proxy, "_user_main_kwargs")
        info = builder._get_schema_info(comp_name)
        handler_name = info.get("handler_name")
        handler = getattr(builder, handler_name) if handler_name else None
        builder_class = info.get("component_builder") or type(builder)
        based_on = info.get("based_on")

        framework_main_kwargs = {
            k[len("main_"):]: v
            for k, v in framework_kwargs.items()
            if k.startswith("main_")
        }
        main_kwargs = {**user_main_kwargs, **framework_main_kwargs}
        user_dp = user_main_kwargs.get("datapath")
        framework_dp = framework_main_kwargs.get("datapath")
        if user_dp and framework_dp:
            main_kwargs["datapath"] = f"{user_dp}{framework_dp}"

        if based_on:
            comp_bag = self._resolve_parent_component(
                based_on, builder, main_kwargs,
            )
        else:
            comp_bag = Component(builder=builder_class)
            comp_bag._skip_parent_validation = True

        result = handler(comp_bag, main_kwargs=main_kwargs) if handler else None

        # Mount slot content into destinations (if the handler returns a
        # ``{slot_name: destination}`` dict).
        slots = object.__getattribute__(proxy, "_slots")
        if slots and isinstance(result, dict):
            for slot_name, dest in result.items():
                source_bag = slots.get(slot_name)
                if source_bag is None or len(source_bag) == 0:
                    continue
                if isinstance(dest, BagNode):
                    if not isinstance(dest.value, Bag):
                        dest.value = BuilderBag(builder=builder_class)
                    dest_bag = dest.value
                else:
                    dest_bag = dest
                for src_node in source_bag:
                    Bag.set_item(
                        dest_bag,
                        src_node.label,
                        src_node.value,
                        _attributes=dict(src_node.attr),
                        node_tag=src_node.node_tag,
                    )

        self._validate_component_tree(comp_bag, comp_name, info)
        return comp_bag

    def _validate_component_tree(
        self, comp_bag: Bag, comp_name: str, info: dict,
    ) -> None:
        """Enforce: exactly one top-level node; match ``main_tag`` if declared.

        A component must produce a tree (single root), not a forest.
        If ``main_tag`` is declared in the schema, the top-level node_tag
        must match it.
        """
        top_count = len(comp_bag)
        if top_count != 1:
            raise ValueError(
                f"Component '{comp_name}' must produce a single top-level node, "
                f"got {top_count}",
            )
        top = next(iter(comp_bag))
        main_tag = info.get("main_tag")
        if main_tag and top.node_tag != main_tag:
            raise ValueError(
                f"Component '{comp_name}' declared main_tag='{main_tag}' "
                f"but produced top-level node_tag='{top.node_tag}'",
            )

    def _resolve_parent_component(
        self, based_on: str, builder: Any, main_kwargs: dict,
    ) -> Bag:
        """Resolve a based_on chain: run the parent handler(s) first.

        Framework ``main_kwargs`` flow down the based_on chain: each
        parent handler receives the same main_kwargs as the leaf.
        """
        parent_info = builder._get_schema_info(based_on)
        parent_handler_name = parent_info.get("handler_name")
        parent_handler = getattr(builder, parent_handler_name) if parent_handler_name else None
        parent_builder_class = parent_info.get("component_builder") or type(builder)
        parent_based_on = parent_info.get("based_on")

        if parent_based_on:
            comp_bag = self._resolve_parent_component(
                parent_based_on, builder, main_kwargs,
            )
        else:
            comp_bag = Component(builder=parent_builder_class)
            comp_bag._skip_parent_validation = True

        if parent_handler:
            parent_handler(comp_bag, main_kwargs=main_kwargs)
        return comp_bag

    def _expand_component_iterate(
        self,
        node: BagNode,
        iterate_raw: str,
        target: Bag,
        data: Bag,
        built_path: str,
    ) -> None:
        """Expand a component N times, once per child in the iterated data.

        For each child, passes ``main_datapath='.{child.label}'`` to the
        handler via framework ``main_kwargs``. The handler splats these
        on the main widget. Resolution of the relative datapath relies
        on ancestors providing an absolute anchor (no fallback).
        """
        pointer_info = parse_pointer(iterate_raw)
        raw_path = pointer_info.path
        if pointer_info.volume is not None:
            raw_path = f"{pointer_info.volume}:{raw_path}"

        data_path = node.abs_datapath(raw_path) if hasattr(node, "abs_datapath") else raw_path
        self._register_dep(data_path, built_path, "build")
        if hasattr(node, "get_relative_data"):
            data_bag = node.get_relative_data(raw_path)
        else:
            data_bag = data.get_item(data_path)

        if not isinstance(data_bag, Bag):
            return

        proxy = node.value
        for child_data_node in data_bag:
            comp_bag = self._expand_component(
                proxy, main_datapath=f".{child_data_node.label}",
            )
            self._build_walk(comp_bag, target, data, built_path)

    # -----------------------------------------------------------------------
    # Dependency registration (for manager's DependencyGraph)
    # -----------------------------------------------------------------------

    def _register_dep(self, source_path: str, target: str, dep_type: str) -> None:
        """Register a dependency edge in the manager's graph.

        No-op if there is no manager or the manager has no graph.
        """
        manager = getattr(self, "_manager", None)
        if manager is None:
            return
        graph = getattr(manager, "_dep_graph", None)
        if graph is None:
            return
        from ..dependency_graph import DepEdge
        graph.add(DepEdge(
            source_path=source_path,
            target=target,
            dep_type=dep_type,
            builder_name=getattr(self, "_builder_name", None),
        ))

    def _register_formula_deps(self, formula_path: str, dep_paths: dict[str, str]) -> None:
        """Register formula dependency edges: each dep_path → formula_path.

        Paths are as ``abs_datapath`` returns them: plain (local) for the
        builder's own data, ``volume:rest`` for cross-builder pointers.
        No automatic prefixing of the builder name.
        """
        for dep_path in dep_paths.values():
            self._register_dep(dep_path, formula_path, "formula")

    def _register_render_deps(self, bag: Bag) -> None:
        """Walk the built bag and register render edges for ^pointer nodes."""
        for node in bag:
            for pointer_info, _location in scan_for_pointers(node):
                # Reconstruct path with volume for abs_datapath resolution
                raw_path = pointer_info.path
                if pointer_info.volume is not None:
                    raw_path = f"{pointer_info.volume}:{raw_path}"
                abs_path = node.abs_datapath(raw_path) if hasattr(node, "abs_datapath") else raw_path
                node_path = node.fullpath if hasattr(node, "fullpath") else node.label
                self._register_dep(abs_path, node_path, "render")
            value = node.get_value(static=True)
            if isinstance(value, Bag):
                self._register_render_deps(value)

    def _process_pending_data_elements(self, data: Bag) -> None:
        """Process accumulated data elements after the built tree is complete.

        Data elements are processed deferred so that abs_datapath can
        resolve relative paths via the built ancestor chain.
        """
        for source_node, built_parent in self._pending_data_elements:
            if source_node.node_tag == "data_setter":
                self._execute_data_setter(source_node, built_parent, data)
            elif source_node.node_tag == "data_formula":
                self._install_formula_resolver(source_node, built_parent, data)
        self._pending_data_elements = []

    def _execute_data_setter(
        self, node: BagNode, context_node: BagNode | None, data: Bag,
    ) -> None:
        """Execute a data_setter. Write value via the built context node.

        Routing (own local_store vs volume) is handled by
        ``context_node.set_relative_data``.
        """
        attrs = dict(node.attr)
        raw_path = attrs.get("_data_path")
        if raw_path is None or context_node is None:
            return

        value = node.current_from_datasource(attrs.get("value"), data) \
            if hasattr(node, "current_from_datasource") else attrs.get("value")
        if isinstance(value, dict):
            value = Bag(source=value)
        context_node.set_relative_data(raw_path, value)

        on_built = attrs.get("_onBuilt")
        if callable(on_built):
            self._infra_on_built_hooks.append(on_built)

    def _install_formula_resolver(
        self, node: BagNode, context_node: BagNode | None, data: Bag,
    ) -> None:
        """Install a FormulaResolver on the target data store.

        Path resolution and volume routing go through
        ``context_node._resolve_target_bag``: the resolver lives on the
        local_store of the volume the path points to, or on the
        builder's own local_store for plain paths.

        Dependency pointers stay as ``^...`` strings in the resolver
        kwargs and are resolved lazily at load time by ``on_loading``
        via ``context_node.get_relative_data``.
        """
        attrs = dict(node.attr)
        raw_path = attrs.get("_data_path")
        if raw_path is None or context_node is None:
            return

        func = attrs.get("func")
        if func is None:
            return

        resolved_path = context_node.abs_datapath(raw_path)
        target_bag, local_path = context_node._resolve_target_bag(resolved_path)

        # Collect kwargs for the resolver: pointers stay as pointers.
        resolver_kwargs: dict[str, Any] = {"func": func}
        for k, v in attrs.items():
            if k.startswith("_") or k == "func":
                continue
            resolver_kwargs[k] = v

        cache_time = attrs.get("_cache_time", 0)
        interval = attrs.get("_interval")
        read_only = cache_time == 0 and interval is None

        resolver = FormulaResolver(
            cache_time=cache_time, interval=interval, read_only=read_only,
            **resolver_kwargs,
        )
        resolver._built_context = context_node

        # Stop old resolver's timer if replacing.
        old_node = target_bag.get_node(local_path)
        if old_node is not None and old_node.resolver is not None:
            old_node.resolver = None

        target_bag.set_resolver(local_path, resolver)

        # Register formula dependency edges in the manager's graph.
        dep_paths = {
            k: context_node.abs_datapath(v[1:])
            for k, v in resolver_kwargs.items()
            if isinstance(v, str) and v.startswith("^")
        }
        self._register_formula_deps(resolved_path, dep_paths)

        # Collect _on_built formula warm-up entries: (target_bag, local_path).
        if attrs.get("_on_built"):
            self._on_built_formula_paths.append((target_bag, local_path))

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

        Two-phase pipeline:
        - Phase 1 (walk): materialize elements and expand components
          into the built bag. Data elements are accumulated for phase 2.
        - Phase 2 (finalize): process data elements (setter/formula)
          using the complete built tree for path resolution, then
          warm up formulas and register render dependencies.

        Does NOT activate reactivity -- call ``subscribe()`` separately.

        Returns None in sync context, or a coroutine in async context.
        """
        self._ensure_reactivity()
        self._clear_built()
        self._infra_on_built_hooks: list[Any] = []
        self._on_built_formula_paths: list[tuple[Bag, str]] = []
        self._pending_data_elements: list[tuple] = []

        walk_result = self._build_walk(
            self.source, self.built, self.data,
        )

        def finalize(_: Any) -> None:
            # Phase 2: process data elements with complete built tree
            self._process_pending_data_elements(self.data)
            # Warm up formula resolvers with _on_built=True. Each entry
            # is (target_bag, local_path) — the target_bag may be a
            # remote volume's local_store.
            for target_bag, local_path in self._on_built_formula_paths:
                target_bag.get_item(local_path)
            self._on_built_formula_paths = []
            for hook in self._infra_on_built_hooks:
                hook(self)
            self._infra_on_built_hooks = []
            # Register render dependency edges from built ^pointers
            self._register_render_deps(self.built)

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
