# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderHandler — supplies data to mounted builders.

A page is a builder; a builder that reads pointers (``^``/``=``) needs a
data source. The BuilderHandler is that source: it owns a single segmented
``_dataroot`` and mounts builders by name, handing each one its own data
segment. It is NOT subclassed and NOT a render engine — rendering lives
on the builder (create/render). The handler only provides the data and
(at read time) tracks which nodes read which paths.

    handler = BuilderHandler()
    handler.add_builder(page)   # mounted under page.name; page.data is its bag

The ``_`` segment is created up front as the shared/common space.
"""
from __future__ import annotations

import functools
import threading
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, NamedTuple

from genro_bag import Bag

from .source_bag import SourceBag, SourceBagNode


class RenderEntry(NamedTuple):
    """One queued render: the event kind, the touched SOURCE path and —
    for the per-row kinds (``row_upd``/``row_ins``/``row_del``) — the
    label of the iterate row the event addressed (CMP.7). A mutation
    that touched ONE leaf of the row carries the residual ``field``
    too (``cell_upd``): the flush may answer with a value-only cell
    patch, no render at all."""

    kind: str
    path: str
    label: str | None = None
    field: str | None = None


#: Above this many touched rows of ONE component in a single flush, the
#: per-row patches coalesce into the enclosing-container replace (the
#: structural flood case). Cell patches never coalesce: value-only ops
#: are exactly what a shared-binding broadcast wants to ship.
ROW_COALESCE_LIMIT = 50

#: Above this many touched CELLS of one row in a single flush, the
#: cell patches collapse into that row's replace (one fragment beats
#: re-reading and shipping most of the row field by field).
CELLS_PER_ROW_LIMIT = 4

#: A formula key draining more than this many times in one flush is a
#: livelock (a -> b -> a): the drain raises naming the rule.
FORMULA_REQUEUE_LIMIT = 50

#: Rows per page of a lazy iterate (the parked snapshot is served in
#: pages of this size; the marker bakes it for the client's
#: ``index // page_size`` arithmetic). Engine constant for now; the
#: parametric form (``lazy=N``) waits for a case that demands it.
LAZY_PAGE_SIZE = 100


class RuleSpec(NamedTuple):
    """One row rule as a TEMPLATE: the body is code, so the rule is
    the same for every row — what varies is the row it runs on.

    ``bindings`` are ``(name, mode, payload)``: mode ``row`` reads the
    payload suffix on the event's row (``.qty``, ``?qty``), ``abs`` an
    absolute path, ``const`` the payload itself. ``destination`` is
    ``(mode, payload)`` (formulas only). ``row_triggers`` are the
    reactive row suffixes (the by-field index keys); ``shared_triggers``
    the reactive absolute paths (registered handler-wide)."""

    kind: str                                    # formula | controller
    func: Any
    bindings: tuple[tuple[str, str, Any], ...]
    destination: tuple[str, str] | None
    row_triggers: tuple[str, ...]
    shared_triggers: tuple[str, ...]
    segment: str                                 # the builder's mount


class ComponentRules(NamedTuple):
    """The rules of ONE component: specs indexed by row trigger.

    ``store_mode`` marks a store-anchored component (no row dimension:
    the residual after the anchor IS the field)."""

    store_mode: bool
    specs: tuple[RuleSpec, ...]
    by_field: dict[str, tuple[RuleSpec, ...]]


class RowContext:
    """The ``node`` a row-rule controller receives.

    Template rules execute against ANY row, so the controller cannot
    get a retained source node (its relative paths would resolve
    against the registration row). This context carries the reactive
    vocabulary bound to the EVENT's row coordinates: ``.x``/``?a``
    resolve on the row, plain paths on the builder segment.
    """

    def __init__(self, data: Bag, segment: str, row_path: str | None):
        self._data = data
        self._segment = segment
        self._row_path = row_path

    def _abs(self, path: str) -> str:
        if path.startswith((".", "?")):
            if self._row_path is None:
                raise ValueError(
                    f"row-relative path {path!r} in a rule with no row",
                )
            return self._row_path + path
        return f"{self._segment}.{path}"

    def GET(self, path: str) -> Any:
        return self._data.get_item(self._abs(path))

    def SET(self, path: str, value: Any) -> None:
        self._data.set_item(self._abs(path), value, _reason=True)

    def PUT(self, path: str, value: Any) -> None:
        self._data.set_item(self._abs(path), value, _reason=False)

    def FIRE(self, path: str, value: Any = True) -> None:
        self._data.set_item(
            self._abs(path), value, _fired=True, _reason=True,
        )


class BuilderHandler:
    """Data source for mounted builders. One segmented ``_dataroot``."""

    def __init__(self, application: Any = None) -> None:
        self.builders: dict[str, Any] = {}
        self.default_builder_name: str | None = None
        self.application: Any = application
        self._dataroot: Bag = Bag()
        self._dataroot["_"] = Bag()        # shared/common segment
        self._dataroot.set_backref()
        # Read-time pointer tracking: key = absolute data path, value =
        # {id(node): node}. Populated by _register_path during render.
        self.pointer_map: dict[str, dict[int, SourceBagNode]] = {}
        # Row logic of the expansions (CMP.7), per-COMPONENT templates:
        # the body is code, so the rule of row 45 IS the rule of row 46
        # — ONE spec per rule per component, never one per row. The
        # event's coordinates (anchor -> row label -> field) resolve
        # which rules run and on which row: a dict hit per prefix, no
        # catalog scan, size independent of the data. Shared bindings
        # (the header exchange rate) are the only absolute entries:
        # one event runs the spec over every live row. Executed in the
        # data-event cascade — NEVER at render (loaded data is trusted
        # as-is; the rule is a rule of MUTATION).
        self.component_rules: dict[str, ComponentRules] = {}
        self.shared_rules: dict[str, list[tuple[str, RuleSpec]]] = {}
        # Armed by activate(): startup is over, the first render has
        # populated the pointer_map. live() requires it — a page never
        # rendered is not reactive yet.
        self._live_enabled: bool = False
        # Live-section state. Private: the only public access is the
        # live() context manager (and the @live method decorator). The
        # RLock makes live() the handler's mutation critical section —
        # sections from other threads queue up, same-thread nesting
        # re-enters and merges into the outermost section (depth).
        self._live_target: Any = None
        self._live_depth: int = 0
        self._live_lock: threading.RLock = threading.RLock()
        # Formula queue of the live section: a write QUEUES the dependent
        # formulas (FIFO, dedup on the pendings); the outermost exit
        # drains it before the render flush. Controllers never queue.
        self._formula_queue: deque[tuple] = deque()
        self._pending_formulas: set[Any] = set()
        # End-of-live render queue: builder name -> touched source nodes.
        self._nodes_to_render: dict[str, list] = {}
        # target_ids of nodes deleted in the current section, captured at
        # the delete event (see record_removed_id).
        self._removed_target_ids: dict[tuple[str, str], str | None] = {}
        # Lazy iterate (CMP.7): parked snapshots (the freezed selection
        # of one query execution) and the reserved fire topics, both
        # keyed by the component's base id. Access ONLY through the
        # lazy_* methods — the backend must stay swappable (in-process
        # dict today, an external store tomorrow).
        self._lazy_parking: dict[str, Any] = {}
        self._lazy_topics: dict[str, tuple[str, SourceBagNode]] = {}
        self.setup(self._dataroot["_"])

    @property
    def data(self) -> Bag:
        """The whole segmented datastore (one ``_dataroot`` per document)."""
        return self._dataroot

    def setup(self, data: Any) -> None:
        """Override point: populate the shared ``_`` segment.

        Receives the common data bag. Default no-op — a custom handler
        overrides it to seed data shared across the mounted builders.
        """

    def add_builder(self, *builders: Any) -> None:
        """Mount builders under their own ``name`` and create each.

        The name belongs to the builder (passed at construction, default
        the dialect typology): mounting reads it, never assigns it, so the
        registration name and the builder name cannot diverge. Mounting a
        second builder with the same name, or one named ``_`` (the shared
        segment), raises.

        Each builder is registered, given its own segment in the
        ``_dataroot``, plugged with ``handler`` (this) and ``data`` (its
        segment bag), and created (``setup`` + ``main`` + first calculation,
        which seeds the data_setters). ``create`` arms the source subscribe
        when reactive; the data subscribe is armed later by :meth:`activate`,
        after the first render has populated the pointer_map.
        """
        for instance in builders:
            name = instance.name
            if not name:
                raise ValueError(
                    f"{type(instance).__name__} has no name: pass one at "
                    "construction or declare a dialect _name",
                )
            if name == "_":
                raise ValueError(
                    "'_' is the shared data segment, not a mount name",
                )
            if name in self.builders:
                raise ValueError(
                    f"a builder named {name!r} is already mounted",
                )
            if self.default_builder_name is None:
                self.default_builder_name = name
            self.builders[name] = instance
            self._dataroot[name] = Bag()
            instance.handler = self
            instance.data = self._dataroot[name]
            # The handler is unique for the whole document; put it on the
            # source root so every node (host or sub-builder) reaches it
            # via the ``handler`` property (Bag.root).
            instance._sourceroot._handler = self
            instance.create()

    def activate(self) -> None:
        """Finish startup: render every builder, then arm data reactivity.

        The first render populates the pointer_map (read-time tracking), so
        the data subscribe — which uses it to find the readers of a mutated
        path — is armed only afterwards. The source subscribe is armed by
        each builder's ``create``.

        Liveness presupposes an application: without one no subscribe is
        armed and ``_live_enabled`` stays off, so ``live()`` raises instead
        of running a critical section where nothing can react.
        """
        for instance in self.builders.values():
            instance.render()
        if self.application:
            self._dataroot.subscribe(
                "builder_data",
                insert=self._on_data_event,
                update=self._on_data_event,
                delete=self._on_data_event,
            )
            self._live_enabled = True

    def _on_data_event(
        self, node: SourceBagNode, evt: str, pathlist: list[str], **kw: Any,
    ) -> None:
        """A data mutation recomputes the dependent logic, then queues renders.

        Derives the changed data path (ins/del: pathlist + the node's label;
        upd: the pathlist itself), collects the readers grouped by builder via
        :meth:`_relevant_nodes`, runs :meth:`execute_logic` (data_formula /
        data_controller recompute, whose writes re-enter here and cascade),
        then queues EVERY reader for the end-of-live render:

        - ``node`` reads exactly the mutated datum;
        - ``container`` reads a leaf inside a container that was replaced
          wholesale;
        - ``child`` reads a container one of whose inner data changed —
          this is how a mutation INSIDE an anchored collection reaches the
          component node that subscribed the anchor (the expansion's own
          pointers are never in the map, CMP.7): the coarse subscription
          catches the fine mutation.

        At Level 0 the flush renders the whole builder once, so queuing
        every kind costs nothing extra; the kind classification is the
        input for the partial-render refinement (per-block re-render via
        path arithmetic on the residual).
        """
        if kw.get("reason") == "autocreate":
            # A container born on the way to a leaf: one deep write is ONE
            # logical mutation. Nothing to compute and nothing to render on
            # the intermediate births — the leaf event of the same write
            # follows at once and reaches every reader (DAT.4).
            return
        if evt in ("ins", "del"):
            path = ".".join([*pathlist, node.label])
        else:
            path = ".".join(pathlist)
        lazy = self._lazy_topics.get(path)
        if lazy is not None:
            # A reserved lazy topic has exactly ONE subscriber — the
            # engine. No rules, no readers: queue the page and leave.
            self._queue_lazy_page(path, lazy[1])
            return
        relevant = self._relevant_nodes(path)
        # Rules dispatch by COORDINATES (no per-row catalog, no scan).
        # A deleted row needs no purge: rules are templates, and the
        # dead row fails the existence check inside the dispatch.
        # Rules BEFORE the page readers: queued formulas drain FIFO, so
        # the order is the layering — the row rules run ahead of the
        # wide readers (a grand total) that depend on their writes.
        self._run_component_rules(path)
        self.execute_logic(relevant)
        for builder, items in relevant.items():
            for kind, view_node in items:
                # Same convention as the source events: key = mount
                # name, path relative to the builder's source (the
                # structural wrapper segment never appears).
                name = view_node.root_builder_name
                rel = view_node.root_builder.source.relative_path(view_node)
                row = self._expansion_row(view_node, path, evt)
                if row is not None:
                    row_kind, label, field = row
                    self.add_render_path(name, rel, row_kind, label, field)
                else:
                    self.add_render_path(name, rel)

    def _expansion_row(
        self, view_node: SourceBagNode, path: str, evt: str,
    ) -> tuple[str, str, str | None] | None:
        """Classify a data event against an iterate component (CMP.7).

        When the reader is an iterate component and the mutated path
        falls under its anchor, the path arithmetic names the row: the
        residual's first segment is the row label. The kind says what
        happened — the row born (``row_ins``), dead (``row_del``),
        replaced wholesale (``row_upd``), or ONE of its leaves changed
        (``cell_upd``, the residual rest as ``field``: the flush may
        answer with a value-only cell patch). ``upd_attrs`` events ride
        as ``row_upd``: the columns travel ON the node, any of them may
        have changed. ``None`` for every other reader (including the
        collection node itself replaced wholesale: the whole block
        re-renders).
        """
        if not view_node._get_meta("component"):
            return None
        if "iterate" not in view_node.attr:
            return None
        if view_node.attr.get("lazy") and evt in ("ins", "del"):
            # A structural event under a LAZY anchor shifts the
            # client's placeholder arithmetic: no per-row patch — fall
            # through to the whole-component re-render (page 0 plus a
            # fresh marker count: cheap by construction). Value events
            # keep the fine classification: a patch addressed to an
            # unpainted row is a client no-op.
            return None
        anchor = view_node.abs_datapath(view_node.attr["iterate"])
        if not path.startswith(anchor + "."):
            return None
        residual = path[len(anchor) + 1:]
        label, _, rest = residual.partition(".")
        if rest:
            return "cell_upd", label, rest
        if evt == "ins":
            return "row_ins", label, None
        if evt == "del":
            return "row_del", label, None
        return "row_upd", label, None

    def set_component_rules(
        self, owner: str, anchor: str | None, store_mode: bool,
        rule_nodes: list, row_prefix: str | None,
    ) -> None:
        """Register a component's rules as TEMPLATES (CMP.7).

        Called by the expansion-registration walk, idempotent: every
        expansion rebuilds its component's entry (the body is code,
        every row builds the same rules — the last wins, atomically:
        the owner's stale shared entries prune first). ``anchor`` keys
        the coordinate dispatch (``None``: an unanchored component,
        whose reactive bindings are all absolute); ``row_prefix`` is
        the registration row's absolute path, the residualization base.
        """
        specs = tuple(
            self._rule_spec(node, row_prefix) for node in rule_nodes
        )
        by_field: dict[str, list[RuleSpec]] = {}
        for spec in specs:
            for suffix in spec.row_triggers:
                by_field.setdefault(suffix, []).append(spec)
        for trigger, entries in list(self.shared_rules.items()):
            kept = [e for e in entries if e[0] != owner]
            if kept:
                self.shared_rules[trigger] = kept
            else:
                del self.shared_rules[trigger]
        for spec in specs:
            for trigger in spec.shared_triggers:
                self.shared_rules.setdefault(trigger, []).append(
                    (owner, anchor, spec),
                )
        if anchor is not None:
            self.component_rules[anchor] = ComponentRules(
                store_mode, specs,
                {key: tuple(value) for key, value in by_field.items()},
            )

    def _rule_spec(self, node: SourceBagNode, row_prefix: str | None) -> RuleSpec:
        """Compile a data-element node into a template spec.

        Bindings residualize against the registration row: a pointer
        landing under ``row_prefix`` becomes a ROW suffix (the same
        suffix for every row — the body is code), anything else stays
        absolute; non-pointer attributes ride as constants. Reactive
        (``^``) bindings are the triggers; passive (``=``) ones read at
        execution only. The func resolves NOW: a missing func fails at
        registration, not at the first event.
        """
        builder = node.builder
        kind = node.node_tag.removeprefix("data_")
        func = builder._resolve_logic_func(node.attr["func"])
        schema_fields = set(builder._get_schema_info(node.node_tag).get(
            "call_args_validations") or {})
        meta_attrs = builder._meta_attrs

        def classify(path: str) -> tuple[str, str]:
            abs_path = node.abs_datapath(path)
            if row_prefix and abs_path.startswith(row_prefix):
                suffix = abs_path[len(row_prefix):]
                if suffix.startswith((".", "?")):
                    return "row", suffix
            return "abs", abs_path

        bindings: list[tuple[str, str, Any]] = []
        row_triggers: list[str] = []
        shared_triggers: list[str] = []
        for name, raw in node.attr.items():
            if name in schema_fields or name in meta_attrs:
                continue
            pointer_kind = node.pointer_type(raw)
            if pointer_kind is None:
                bindings.append((name, "const", raw))
                continue
            mode, payload = classify(raw)
            bindings.append((name, mode, payload))
            if pointer_kind == "^":
                if mode == "row":
                    # the by-field index key: the event field arrives
                    # without the leading dot
                    row_triggers.append(payload.removeprefix("."))
                else:
                    shared_triggers.append(payload)
        destination = None
        if kind == "formula":
            destination = classify(node.attr["destination"])
        return RuleSpec(
            kind, func, tuple(bindings), destination,
            tuple(row_triggers), tuple(shared_triggers),
            node.root_builder_name,
        )

    def _run_component_rules(self, path: str) -> None:
        """Coordinate dispatch (CMP.7): the event path DECOMPOSES.

        Walk the path's prefixes for the deepest registered anchor
        (nested iterates: the inner anchor is the longer prefix); the
        next segment is the row, the rest the field. The field hits
        the by-field index; a row-level event (no field: wholesale
        replace, attr-mode ``upd_attrs``) runs every rule of the
        component. A DEAD row runs nothing: the existence check is the
        resurrection guard — a deleted subtree has no node, so its
        rules can never write it back to life. Shared triggers resolve
        from their own registry (size: components x shared bindings,
        independent of the data): each spec runs over every live row
        of its component. No structure here grows with the row count.
        """
        segments = path.split(".")
        for cut in range(len(segments) - 1, 0, -1):
            anchor = ".".join(segments[:cut])
            component = self.component_rules.get(anchor)
            if component is None:
                continue
            residual = segments[cut:]
            if component.store_mode:
                row_path, field = anchor, ".".join(residual)
            else:
                row_path = f"{anchor}.{residual[0]}"
                field = ".".join(residual[1:])
            if self._dataroot.get_node(row_path) is not None:
                for spec in self._rules_for(component, field):
                    self._dispatch_rule(spec, row_path)
            break
        matched: list[tuple[str, str | None, RuleSpec]] = []
        for trigger, entries in self.shared_rules.items():
            stripped = trigger.split("?", 1)[0]
            if stripped == path or stripped.startswith(path + "."):
                matched.extend(entries)
        seen: set[int] = set()
        for _owner, anchor, spec in matched:
            if id(spec) in seen:
                continue
            seen.add(id(spec))
            self._run_shared_rule(spec, anchor)

    def _rules_for(
        self, component: ComponentRules, field: str,
    ) -> list[RuleSpec]:
        """The specs the mutated ``field`` triggers, deduped in order.

        Exact hit on the by-field index, plus the bindings sitting
        UNDER the mutated field (a container replaced wholesale; the
        ``?attr`` tail strips like everywhere). The index is
        per-component — scanning it is O(own fields), never O(data).
        """
        if not field:
            return list(dict.fromkeys(component.specs))
        hits = list(component.by_field.get(field, ()))
        for suffix, specs in component.by_field.items():
            if suffix == field:
                continue
            stripped = suffix.split("?", 1)[0]
            if stripped == field or stripped.startswith(field + "."):
                hits.extend(specs)
        return list(dict.fromkeys(hits))

    def _dispatch_rule(self, spec: RuleSpec, row_path: str | None) -> None:
        """Run a controller now, queue a formula (inside a live section).

        A command is not a function of the state: two commands are two
        executions, and the FIRE payload does not persist — controllers
        stay synchronous. A formula IS a function of the state: inside
        a live section it defers to the flush drain (one execution on
        the settled inputs); outside there is no flush coming, so it
        executes at once.
        """
        if spec.kind == "formula" and self._live_depth:
            self._enqueue_formula(
                (id(spec), row_path), ("rule", spec, row_path),
            )
        else:
            self._execute_rule(spec, row_path)

    def _enqueue_formula(self, key: Any, entry: tuple) -> None:
        """Queue one formula execution, deduped on the pendings.

        ``key`` identifies the computation — ``(id(spec), row_path)``
        for a component rule, ``id(node)`` for a page data-element —
        and a key already PENDING does not queue twice: when it drains
        it will read the settled inputs anyway. Re-queueing AFTER the
        execution is legitimate (a new input arrived during the drain);
        the dedup is only on the pendings.
        """
        if key in self._pending_formulas:
            return
        self._pending_formulas.add(key)
        self._formula_queue.append((key, *entry))

    def _drain_formulas(self) -> None:
        """Execute the queued formulas until the queue is dry (FIFO).

        Runs at the outermost live() exit, BEFORE the render flush. The
        FIFO order is the layering: the cascade queued the row rules
        ahead of the wide page readers (a grand total), so each formula
        reads the settled state of the layer below. The writes re-enter
        the cascade — controllers run at once, formulas re-queue (dedup
        on the pendings). A rule whose row DIED while queued runs
        nothing: the existence check is the resurrection guard, as in
        the dispatch. A key draining more than
        :data:`FORMULA_REQUEUE_LIMIT` times is a livelock (a -> b -> a):
        explicit error naming the rule.
        """
        counts: dict[Any, int] = {}
        while self._formula_queue:
            key, kind, owner, payload = self._formula_queue.popleft()
            self._pending_formulas.discard(key)
            counts[key] = counts.get(key, 0) + 1
            if counts[key] > FORMULA_REQUEUE_LIMIT:
                if kind == "rule":
                    name = f"rule {owner.func.__name__!r} on {payload!r}"
                else:
                    name = f"data-element {payload.attr.get('func')!r}"
                raise RuntimeError(
                    f"formula livelock: {name} re-queued more than "
                    f"{FORMULA_REQUEUE_LIMIT} times in one flush",
                )
            if kind == "rule":
                if payload is not None and (
                    self._dataroot.get_node(payload) is None
                ):
                    continue          # the row died while queued
                self._execute_rule(owner, payload)
            else:
                owner.compute_logic([payload])

    def _execute_rule(self, spec: RuleSpec, row_path: str | None) -> None:
        """Run one template spec on one row: read, compute, write.

        Everything resolves by coordinates — row suffixes on
        ``row_path``, absolutes as they are, constants as themselves.
        A controller's ``node`` is a :class:`RowContext` bound to the
        same coordinates. The writes re-enter the cascade as any
        canonical data-element write.
        """
        kwargs: dict[str, Any] = {}
        for name, mode, payload in spec.bindings:
            if mode == "const":
                kwargs[name] = payload
            elif mode == "row":
                kwargs[name] = self._dataroot.get_item(row_path + payload)
            else:
                kwargs[name] = self._dataroot.get_item(payload)
        if spec.kind == "formula":
            mode, payload = spec.destination
            dest = row_path + payload if mode == "row" else payload
            self._dataroot.set_item(dest, spec.func(**kwargs), _reason=True)
        else:
            context = RowContext(self._dataroot, spec.segment, row_path)
            spec.func(context, **kwargs)

    def _run_shared_rule(self, spec: RuleSpec, anchor: str | None) -> None:
        """A shared trigger fired: run the spec over its component.

        An iterate component runs the spec once per LIVE row (the
        collection enumerates them: dead rows are simply not there); a
        store component runs it on the store; an unanchored one runs
        it once with no row.
        """
        if anchor is None:
            self._dispatch_rule(spec, None)
            return
        component = self.component_rules.get(anchor)
        if component is None or component.store_mode:
            self._dispatch_rule(spec, anchor)
            return
        collection = self._dataroot.get_item(anchor)
        if collection is None:
            return
        for label in list(collection.keys()):
            self._dispatch_rule(spec, f"{anchor}.{label}")

    def execute_logic(
        self, relevant: dict[Any, list[tuple[str, SourceBagNode]]],
    ) -> None:
        """Recompute the data-element readers, delegating to each builder.

        ``relevant`` is grouped by builder (from :meth:`_relevant_nodes`);
        for each builder the data-element nodes (``data_formula`` /
        ``data_controller``) are passed to its own ``compute_logic`` — the
        logic lives on the builder, the handler only routes each node to its
        owner. Plain view readers (no ``data_element`` meta) are skipped here:
        they only re-render. The compute writes downstream data, which
        re-enters :meth:`_on_data_event` and cascades.

        Inside a live section the FORMULAS do not compute: they queue
        (dedup on the pendings, key = the node) for the flush drain —
        a wide reader used to run once per EVENT, N times on a
        broadcast. Setters and controllers stay synchronous.
        """
        for builder, items in relevant.items():
            for _, node in items:
                if not node._get_meta("data_element"):
                    continue
                if node.node_tag == "data_formula" and self._live_depth:
                    self._enqueue_formula(id(node), ("node", builder, node))
                else:
                    builder.compute_logic([node])

    def lazy_park(self, key: str, snapshot: Any) -> tuple[int, int]:
        """Park a lazy iterate's snapshot (the freezed selection).

        ONE query execution, served in logical pages of
        :data:`LAZY_PAGE_SIZE`: every page of the same key comes from
        the same snapshot — no data shear between page 2 and page 7.
        Re-parking (a re-render re-ran the query) drops the old entry.
        Returns ``(total rows, page size)`` for the marker to bake.
        """
        self.lazy_drop(key)
        self._lazy_parking[key] = snapshot
        return len(snapshot), LAZY_PAGE_SIZE

    def lazy_page(self, key: str, page: int) -> tuple[Any, list[str]]:
        """The parked snapshot and the row labels of ONE page.

        Raises on a key never parked or a page out of range: a client
        asking for what no marker announced is a broken conversation,
        not a case to absorb.
        """
        snapshot = self._lazy_parking.get(key)
        if snapshot is None:
            raise KeyError(f"no parked snapshot for lazy iterate {key!r}")
        try:
            labels = self.lazy_page_of(snapshot, page)
        except ValueError:
            raise ValueError(
                f"lazy page {page} out of range for {key!r}",
            ) from None
        return snapshot, labels

    def lazy_page_of(self, collection: Any, page: int) -> list[str]:
        """The row labels of ONE page of ``collection`` — the slicing
        shared by the parked (read_only) and the store-backed (mutable)
        lazy: the latter has no parking, pages slice the LIVE
        collection at request time. Out of range raises.
        """
        labels = list(collection.keys())[
            page * LAZY_PAGE_SIZE:(page + 1) * LAZY_PAGE_SIZE
        ]
        if page < 0 or not labels:
            raise ValueError(f"lazy page {page} out of range")
        return labels

    def lazy_drop(self, key: str) -> None:
        """Forget a parked snapshot and its topic subscription."""
        self._lazy_parking.pop(key, None)
        for topic, (owner, _node) in list(self._lazy_topics.items()):
            if owner == key:
                del self._lazy_topics[topic]

    def lazy_subscribe(self, key: str, comp_node: SourceBagNode) -> None:
        """Subscribe the engine to a lazy component's reserved topic.

        The marker bakes ``data-fire-pointer="_lazy.<key>"``: the fire
        lands on :meth:`_on_data_event` and queues a ``page`` render
        entry — the subscriber is MACHINERY, no data_controller node.
        """
        topic = comp_node.abs_datapath(f"_lazy.{key}")
        self._lazy_topics[topic] = (key, comp_node)

    def _queue_lazy_page(self, topic: str, comp_node: SourceBagNode) -> None:
        """A fire on a reserved lazy topic asks for ONE page.

        The payload MUST be the page number (the client fires
        ``index // page_size``); anything else is a protocol error.
        The flush turns the queued entry into the ``page`` op, rendered
        from the parking.
        """
        value = self._dataroot.get_item(topic)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"lazy page request on {topic!r} wants an integer "
                f"page number, got {value!r}",
            )
        name = comp_node.root_builder_name
        rel = comp_node.root_builder.source.relative_path(comp_node)
        self.add_render_path(name, rel, "page", str(value))

    @contextmanager
    def live(self, target: Any = None) -> Iterator[BuilderHandler]:
        """The handler's mutation critical section: batch, then render.

        Whoever mutates the document (source or data) does it inside
        ``with handler.live():`` — entering acquires the handler's RLock,
        so sections from other threads queue up and each one sees (and
        flushes) a consistent state. The reactive cascade triggered by a
        mutation runs synchronously inside the same section: no
        re-acquisition involved.

        Same-thread nesting re-enters the lock and MERGES into the
        outermost section: one queue, one flush at the outermost exit
        (an inner section cannot set a ``target``). Each source/data
        event records its touched path via :meth:`add_render_path`; the
        outermost exit first DRAINS the formula queue (the section's
        writes queued the dependent formulas, deduped: each one runs on
        the settled state, not once per event), then the flush renders
        every builder with at least one touched node, toward ``target``
        when given (it wins over the registered default for this
        section only).

        Requires an application and :meth:`activate` (RuntimeError
        otherwise): liveness is forbidden outside an application — a
        handler without one has no subscribes, nothing would react.
        """
        if not self._live_enabled:
            raise RuntimeError(
                "live() requires an activated handler with an application: "
                "without them nothing is subscribed, nothing would react",
            )
        with self._live_lock:
            if self._live_depth and target is not None:
                raise ValueError("a nested live() section cannot set a target")
            self._live_depth += 1
            if self._live_depth == 1:
                self._nodes_to_render = {}
                self._removed_target_ids = {}
                self._live_target = target
            try:
                yield self
            finally:
                if self._live_depth == 1:
                    # Outermost exit: drain the formula queue while the
                    # section is still open (the executions write, the
                    # writes re-enter the cascade and queue renders),
                    # THEN flush at depth zero (render-time events must
                    # not queue again).
                    try:
                        self._drain_formulas()
                    finally:
                        self._live_depth -= 1
                        try:
                            for name, nodes in self._nodes_to_render.items():
                                if nodes:
                                    self.builders[name].render_nodes(
                                        self._optimize_render(nodes),
                                        target=self._live_target,
                                    )
                        finally:
                            self._nodes_to_render = {}
                            self._removed_target_ids = {}
                            self._live_target = None
                            self._formula_queue.clear()
                            self._pending_formulas.clear()
                else:
                    self._live_depth -= 1

    def add_render_path(
        self, builder_name: str, path: str, kind: str = "upd",
        label: str | None = None, field: str | None = None,
    ) -> None:
        """Record a touched path and its event kind for the end-of-live render.

        ``builder_name`` is the segment the path belongs to; ``path`` is the
        path inside that builder. A source event queues the changed node's
        path with its structural kind (``ins``/``del`` address the child,
        ``upd`` the node); a data event queues each reader's path as
        ``upd`` (a reader re-renders, it never changes shape) — except
        the iterate-component readers, whose events classify PER ROW
        (``row_*`` kinds, ``label`` = the row): the flush patches one
        block instead of the whole container. The end-of-live flush
        renders every builder whose queue is non-empty.

        Outside a live section nothing is recorded: there is no flush
        coming, queueing would only pile up work nobody consumes.
        """
        if not self._live_depth:
            return
        self._nodes_to_render.setdefault(builder_name, []).append(
            RenderEntry(kind, path, label, field),
        )

    def record_removed_id(
        self, builder_name: str, path: str, target_id: str | None,
    ) -> None:
        """Capture a deleted node's ``target_id`` for the flush.

        The node is gone from the source by flush time, so the id that
        addresses its DOM element is taken at the delete event, while
        the node is still in hand. First delete wins: with a
        delete/re-insert pair on the same path, the DOM holds the
        ORIGINAL element — the re-inserted one never reached it.
        """
        if not self._live_depth:
            return
        self._removed_target_ids.setdefault((builder_name, path), target_id)

    def removed_target_id(self, builder_name: str, path: str) -> str | None:
        """The ``target_id`` captured for a node deleted in this section."""
        return self._removed_target_ids.get((builder_name, path))

    def _optimize_render(self, entries: list) -> list:
        """Reduce the queued :class:`RenderEntry` list to the minimal set.

        Per-key netting first (the key is ``(path, label)`` — a plain
        node or ONE row of an iterate component): the section's history
        collapses to its net effect (the flush renders the FINAL source
        state, so only the net shape matters):

        - ``upd`` after ``ins`` is absorbed (the insert renders fresh);
        - ``del`` after ``ins`` cancels BOTH (born and died here: the DOM
          never saw the node);
        - ``ins`` after ``del`` (same label re-inserted, possibly
          elsewhere) nets to ``del`` + ``ins``: remove the old element,
          insert the fresh one at its final position;
        - transitions the bag cannot produce (``ins`` over a live node,
          anything after an un-reinserted ``del``) raise.

        Then the reductions:

        - **exact dedup** — the netting dict itself (first touch wins the
          order);
        - **ancestor covers descendant** — whatever the kinds: a replaced
          or inserted ancestor renders its final subtree, a removed
          ancestor takes the subtree away with it. A whole-node entry on
          a component path covers that component's row entries.
        - **density coalescing** — above :data:`ROW_COALESCE_LIMIT`
          touched rows of one component, the per-row patches collapse
          into the plain ``upd`` of the component (the broadcast case:
          one container fragment beats thousands of row patches).
        """
        state: dict[tuple[str, str | None, str | None], str] = {}
        for kind, path, label, field in entries:
            key = (path, label, field)
            base = kind.removeprefix("row_").removeprefix("cell_")
            prev = state.get(key)
            if prev is None:
                state[key] = base
            elif base == "upd":
                if prev == "del":
                    raise ValueError(
                        f"update queued for {key!r} after its delete",
                    )
                # upd / ins / del+ins all render fresh at flush: absorbed.
            elif base == "ins":
                if prev != "del":
                    raise ValueError(
                        f"insert queued for {key!r} over a live node",
                    )
                state[key] = "del+ins"
            elif base == "del":
                if prev == "ins":
                    del state[key]           # ephemeral: net nothing
                elif prev == "del":
                    raise ValueError(
                        f"delete queued for {key!r} after its delete",
                    )
                else:
                    state[key] = "del"
        whole_paths = {
            path for path, label, field in state if label is None
        }
        row_keys = {
            (path, label) for path, label, field in state
            if label is not None and field is None
        }
        kept = [
            (kind, path, label, field)
            for (path, label, field), kind in state.items()
            # an ancestor whole-node entry renders its final subtree
            if not any(
                other != path and path.startswith(other + ".")
                for other in whole_paths
            )
            # the component's own entry covers its rows and cells
            and not (label is not None and path in whole_paths)
            # the row's own entry covers its cells
            and not (field is not None and (path, label) in row_keys)
        ]
        # Density, cells first: too many cells of ONE row collapse into
        # that row's replace...
        cell_load: dict[tuple[str, str | None], int] = {}
        for kind, path, label, field in kept:
            if field is not None:
                key = (path, label)
                cell_load[key] = cell_load.get(key, 0) + 1
        full_rows = {
            key for key, count in cell_load.items()
            if count > CELLS_PER_ROW_LIMIT
        }
        if full_rows:
            kept = [
                (kind, path, label, field)
                for kind, path, label, field in kept
                if not (field is not None and (path, label) in full_rows)
            ] + [("upd", path, label, None) for path, label in full_rows]
        # ...then rows: a structural flood coalesces into the container
        # replace. CELL entries never count here — value-only ops are
        # exactly what a broadcast wants to ship.
        row_load: dict[str, int] = {}
        for kind, path, label, field in kept:
            if label is not None and field is None and kind != "page":
                row_load[path] = row_load.get(path, 0) + 1
        coalesced = {
            path for path, count in row_load.items()
            if count > ROW_COALESCE_LIMIT
        }
        out: list[RenderEntry] = []
        for path in coalesced:
            out.append(RenderEntry("upd", path))
        for kind, path, label, field in kept:
            if label is not None and path in coalesced:
                continue          # the container replace covers them all
            if kind == "del+ins":
                row = "row_" if label is not None else ""
                out.append(RenderEntry(f"{row}del", path, label))
                out.append(RenderEntry(f"{row}ins", path, label))
            elif kind == "page":
                # Lazy iterate: the label is the page number, not a
                # row — never a row_* op, never coalesced.
                out.append(RenderEntry("page", path, label))
            elif field is not None:
                out.append(RenderEntry("cell_upd", path, label, field))
            elif label is not None:
                out.append(RenderEntry(f"row_{kind}", path, label))
            else:
                out.append(RenderEntry(kind, path))
        return out

    def _register_path(self, node: SourceBagNode, abs_path: str) -> None:
        """Register ``node`` as a reader of ``abs_path`` (read-time tracking).

        No-op without an application: the pointer_map only feeds the
        reactive cascade, so a one-shot render need not pay for it.
        """
        if not self.application:
            return
        self.pointer_map.setdefault(abs_path, {})[id(node)] = node

    def _unregister_pointer(self, node: SourceBagNode) -> None:
        """Drop ``node`` (and its subtree) from ``self.pointer_map``.

        The add side is the render's job (read-time ``_register_path``);
        removal is the explicit action, because a re-render never visits
        the nodes that disappeared. Recurses into the ``SourceBag``
        subtree so a removed branch is fully purged. Silent when a path
        or node is not registered.
        """
        self._update_pointer_map(node, node.pointers())
        if isinstance(node.value, SourceBag):
            for child in node.value:
                self._unregister_pointer(child)

    def _update_pointer_map(
        self,
        node: SourceBagNode,
        pointers: list[tuple[str, str]],
    ) -> None:
        """Remove ``pointers`` of ``node`` from ``self.pointer_map``.

        Each entry is ``(attrname, pointer_str)``: ``attrname=""`` for a
        pointer on ``node.value``, otherwise the attribute name. The path
        entry is pruned when it becomes empty.
        """
        for attrname, pointer in pointers:
            path = node.abs_datapath(pointer)
            if attrname:
                path = f"{path}?{attrname}"
            inner = self.pointer_map.get(path)
            if inner is not None:
                inner.pop(id(node), None)
                if not inner:
                    del self.pointer_map[path]

    def _relevant_nodes(
        self, path: str,
    ) -> dict[Any, list[tuple[str, SourceBagNode]]]:
        """Source nodes that read the mutated data ``path``, grouped by builder.

        Each match is classified against the registered path ``kp`` (the
        pointer_map key, minus any ``?attr`` suffix):

        - ``node``      — ``kp == path``: reads exactly the mutated datum;
        - ``container`` — ``kp`` starts with ``path``: reads a leaf inside it;
        - ``child``     — ``path`` starts with ``kp``: reads a container whose
          child changed.

        Returns ``{builder: [(kind, node), ...]}``, deduped by node id. One
        data path may be read by nodes of several builders (a shared ``_``
        datum), so grouping by ``node.builder`` lets the caller delegate the
        compute to each owning builder and render each one.
        """
        seen: set[int] = set()
        grouped: dict[Any, list[tuple[str, SourceBagNode]]] = {}
        for key, inner in self.pointer_map.items():
            kp = key.split("?", 1)[0]
            if kp == path:
                kind = "node"
            elif kp.startswith(path + "."):
                kind = "container"
            elif path.startswith(kp + "."):
                kind = "child"
            else:
                continue
            for node_id, node in inner.items():
                if node_id in seen:
                    continue
                seen.add(node_id)
                grouped.setdefault(node.builder, []).append((kind, node))
        return grouped


def live(func: Any) -> Any:
    """Method decorator: the whole method is a live section.

    Sugar over ``with handler.live():`` for methods that are mutation
    entry points (a websocket message handler, an RPC). The handler is
    found on the instance: ``self`` itself when the method lives on a
    ``BuilderHandler``, ``self.handler`` otherwise (apps and builders
    both carry one).

        class WsLiveApp(...):
            @live
            def on_ws_message(self, path, value):
                self.handler.data.set_item(path, value)

    Use the context manager directly when the section must be narrower
    than the method or needs a per-section ``target``.
    """
    @functools.wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        handler = self if isinstance(self, BuilderHandler) else self.handler
        with handler.live():
            return func(self, *args, **kwargs)
    return wrapper
