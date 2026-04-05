# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Build mixin: source-to-built materialization, pointer resolution,
binding registration, and source-change handlers (incremental compile).

Handles the complete build pipeline: ``build()`` walks the source Bag,
processes data elements, materializes normal elements into the built Bag,
registers pointer bindings, and resolves ^pointers just-in-time.
Source-change handlers (``_on_source_inserted/updated/deleted``) support
incremental updates after ``subscribe()``.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from genro_bag import Bag
from genro_toolbox.smarttimer import cancel_timer, set_interval

from ..builder_bag import BuilderBag
from ..pointer import is_pointer, parse_pointer, scan_for_pointers

if TYPE_CHECKING:
    from genro_bag import BagNode


class _BuildMixin:
    """Mixin for build walk, pointer resolution, bindings, and source changes."""

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
    ) -> None:
        """Recursive walk: two-pass processing.

        Pass 1: Process data_element nodes (side effects on data Bag).
        Pass 2: Materialize normal elements and components in built.

        Args:
            source: The source Bag to compile from.
            target: The built Bag to populate.
            data: Data Bag for ^pointer resolution.
            binding: BindingManager for subscription registration.
            prefix: Path prefix for subscription map keys.
        """
        # Pass 1: process data_element nodes
        for node in source:
            if node.attr.get("_is_data_element"):
                self._process_infra_node(node, data)

        # Pass 2: materialize normal nodes
        for node in source:
            if node.attr.get("_is_data_element"):
                continue

            built_path = f"{prefix}.{node.label}" if prefix else node.label

            binding.unbind_path(built_path)

            value = node.get_value(static=False) if node.resolver is not None else node.static_value

            new_node = target.set_item(
                node.label,
                value if not isinstance(value, Bag) else BuilderBag(builder=type(self)),
                _attributes=dict(node.attr),
                node_tag=node.node_tag,
            )

            self._register_bindings(new_node, built_path, data, binding)

            if isinstance(value, Bag):
                self._build_walk(value, new_node.value, data, binding, prefix=built_path)

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
            if is_pointer(v):
                resolved[k] = self._resolve_pointer_from_data(v, node, data)
            else:
                resolved[k] = v
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
            datapath = ""
            if pointer_info.is_relative and hasattr(node, "_resolve_datapath"):
                datapath = node._resolve_datapath()

            data_path = pointer_info.path
            if pointer_info.is_relative:
                rel = data_path[1:]
                data_path = f"{datapath}.{rel}" if datapath else rel

            data_key = f"{data_path}?{pointer_info.attr}" if pointer_info.attr else data_path
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

    def _resolve_pointer(
        self, node: BagNode, pointer_info: Any, data_path: str, data: Bag,
    ) -> Any:
        """Resolve a single ^pointer value from the data Bag."""
        if hasattr(node, "_get_relative_data"):
            return node._get_relative_data(data, pointer_info.raw[1:])

        if pointer_info.attr:
            data_node = data.get_node(data_path)
            return data_node.attr.get(pointer_info.attr) if data_node else None
        return data.get_item(data_path)

    def _resolve_pointer_from_data(
        self, raw: str, node: BagNode, data: Bag,
    ) -> Any:
        """Resolve a ^pointer string to its current value from data.

        Used by _resolve_node for just-in-time resolution during render/compile.
        The built node is NOT modified.
        """
        pointer_info = parse_pointer(raw)

        data_path = pointer_info.path
        if pointer_info.is_relative and hasattr(node, "_resolve_datapath"):
            datapath = node._resolve_datapath()
            rel = data_path[1:]
            data_path = f"{datapath}.{rel}" if datapath else rel

        return self._resolve_pointer(node, pointer_info, data_path, data)

    def _resolve_node(self, node: BagNode, data: Bag) -> dict[str, Any]:
        """Produce a resolved view of a built node.

        Returns a dict with resolved value and attributes. The built node
        is NOT modified -- ^pointer strings stay in the built Bag.

        Handles three kinds of attribute values:
        - ^pointer strings: resolved from data
        - callables: defaults inspected for ^pointer deps, called with resolved args
        - plain values: passed through

        Used by renderer/compiler _build_context for just-in-time resolution.
        """
        raw_value = node.get_value(static=True)

        resolved_value = raw_value
        if is_pointer(raw_value):
            resolved_value = self._resolve_pointer_from_data(raw_value, node, data)

        resolved_attrs: dict[str, Any] = {}
        for k, v in node.attr.items():
            if is_pointer(v):
                resolved_attrs[k] = self._resolve_pointer_from_data(v, node, data)
            elif callable(v) and not k.startswith("_"):
                resolved_attrs[k] = self._resolve_computed_attr(v, node, data)
            else:
                resolved_attrs[k] = v

        return {
            "node_value": resolved_value,
            "attrs": resolved_attrs,
            "node": node,
        }

    def _resolve_computed_attr(
        self, func: Any, node: BagNode, data: Bag,
    ) -> Any:
        """Resolve a computed attribute (callable with ^pointer defaults).

        Inspects the callable's parameter defaults for ^pointer strings,
        resolves them from data, and calls the callable with resolved values.
        """
        sig = inspect.signature(func)
        kwargs: dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            if param.default is inspect.Parameter.empty:
                continue
            default = param.default
            if is_pointer(default):
                kwargs[param_name] = self._resolve_pointer_from_data(default, node, data)
            else:
                kwargs[param_name] = default
        return func(**kwargs)

    # -----------------------------------------------------------------------
    # Build / subscribe / rebuild
    # -----------------------------------------------------------------------

    def build(self) -> None:
        """Materialize source -> built.

        Two-pass walk: data_elements first, then normal elements.
        After walk, sorts formula by dependency order and calls _onBuilt hooks.
        Does NOT activate reactivity -- call ``subscribe()`` separately.
        """
        self._clear_built()
        self._formula_registry = {}
        self._formula_order: list[str] = []
        self._infra_on_built_hooks: list[Any] = []

        self._build_walk(
            self.source, self.built, self.data, self._binding,
        )

        self._formula_order = self._topological_sort_formulas()

        for hook in self._infra_on_built_hooks:
            hook(self)
        self._infra_on_built_hooks = []

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
    ) -> None:
        """Called when a node is inserted into the source."""
        if not self._auto_compile or node is None:
            return

        # Data element: process as infra and re-render
        if node.attr.get("_is_data_element"):
            self._process_infra_node(node, self.data)
            self._rerender()
            return

        parent_path = ".".join(str(p) for p in pathlist) if pathlist else ""

        if parent_path:
            target_bag = self.built.get_item(parent_path)
            if not isinstance(target_bag, Bag):
                return
        else:
            target_bag = self.built

        node_path = f"{parent_path}.{node.label}" if parent_path else node.label

        value = node.get_value(static=False) if node.resolver is not None else node.static_value

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

        self._rerender()

    def _on_source_updated(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node in the source is updated (value or attributes)."""
        if not self._auto_compile or pathlist is None:
            return

        # Data element: re-process and re-render
        if node is not None and node.attr.get("_is_data_element"):
            self._process_infra_node(node, self.data)
            self._rerender()
            return

        path = ".".join(str(p) for p in pathlist)
        built_node = self.built.get_node(path)
        if built_node is None:
            return

        if evt == "upd_value":
            value = node.get_value(static=False) if node.resolver is not None else node.static_value

            self._binding.unbind_path(path)

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

        elif evt == "upd_attrs":
            if node is not None:
                built_node.set_attr(dict(node.attr))
                self._binding.unbind_path(path)
                self._register_bindings(
                    built_node, path, self.data, self._binding,
                )

        self._rerender()
