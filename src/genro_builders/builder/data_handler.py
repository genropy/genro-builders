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
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, NamedTuple

from genro_bag import Bag

from .source_bag import SourceBag, SourceBagNode


class RenderEntry(NamedTuple):
    """One queued render: the event kind, the touched SOURCE path and —
    for the per-row kinds (``row_upd``/``row_ins``/``row_del``) — the
    label of the iterate row the event addressed (CMP.7)."""

    kind: str
    path: str
    label: str | None = None


#: Above this many touched rows of ONE component in a single flush, the
#: per-row patches coalesce into the enclosing-container replace (the
#: shared-binding broadcast — e.g. an exchange rate over every row —
#: ships better as one fragment than as thousands).
ROW_COALESCE_LIMIT = 50


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
        # Row logic of the expansions (CMP.7): trigger path ->
        # {id(node): (data-element node, row prefix)}. A row recomputes
        # iff the mutated path is among ITS resolved bindings — a
        # row-internal binding fires one row, a shared one (the header
        # exchange rate) fires every row that reads it. Populated by
        # the expansion-registration walk, purged by row prefix at
        # re-expansion, executed in the data-event cascade — NEVER at
        # render (loaded data is trusted as-is; the rule is a rule of
        # MUTATION).
        self.expansion_logic: dict[
            str, dict[int, tuple[SourceBagNode, str]]
        ] = {}
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
        # End-of-live render queue: builder name -> touched source nodes.
        self._nodes_to_render: dict[str, list] = {}
        # target_ids of nodes deleted in the current section, captured at
        # the delete event (see record_removed_id).
        self._removed_target_ids: dict[tuple[str, str], str | None] = {}
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
        relevant = self._relevant_nodes(path)
        self.execute_logic(relevant)
        if evt == "del":
            # Deleting a subtree KILLS the rules anchored in it: a dead
            # row's rule must never run (its destination write would
            # autocreate the row back). Eager purge — waiting for the
            # re-expansion would leave stale rules live for the rest of
            # the cascade (a shared binding would resurrect the row).
            # Rules merely READING under the deleted path survive: their
            # anchor is elsewhere, and they recompute right below.
            self._purge_anchored_rules(path)
        self._execute_expansion_logic(path)
        for builder, items in relevant.items():
            for kind, view_node in items:
                # Same convention as the source events: key = mount
                # name, path relative to the builder's source (the
                # structural wrapper segment never appears).
                name = view_node.root_builder_name
                rel = view_node.root_builder.source.relative_path(view_node)
                row = self._expansion_row(view_node, path, evt)
                if row is not None:
                    row_kind, label = row
                    self.add_render_path(name, rel, row_kind, label)
                else:
                    self.add_render_path(name, rel)

    def _expansion_row(
        self, view_node: SourceBagNode, path: str, evt: str,
    ) -> tuple[str, str] | None:
        """Classify a data event against an iterate component (CMP.7).

        When the reader is an iterate component and the mutated path
        falls under its anchor, the path arithmetic names the row: the
        residual's first segment is the row label. The kind says what
        happened to it — a field changed or the row replaced wholesale
        (``row_upd``), the row born (``row_ins``) or dead (``row_del``).
        ``None`` for every other reader (including the collection node
        itself replaced wholesale: the whole block re-renders).
        """
        if not view_node._get_meta("component"):
            return None
        if "iterate" not in view_node.attr:
            return None
        anchor = view_node.abs_datapath(view_node.attr["iterate"])
        if not path.startswith(anchor + "."):
            return None
        residual = path[len(anchor) + 1:]
        label, _, rest = residual.partition(".")
        if rest:
            return "row_upd", label
        if evt == "ins":
            return "row_ins", label
        if evt == "del":
            return "row_del", label
        return "row_upd", label

    def register_expansion_logic(
        self, abs_path: str, node: SourceBagNode, prefix: str,
    ) -> None:
        """Register a row rule's trigger: ``abs_path`` recomputes ``node``.

        ``node`` is the retained data-element of ONE row expansion,
        anchored to its row: executing it computes that row. ``prefix``
        is the row's derived-identity prefix, the purge key.
        """
        self.expansion_logic.setdefault(abs_path, {})[id(node)] = (
            node, prefix,
        )

    def purge_expansion_logic(self, prefix: str) -> None:
        """Drop every rule registered under ``prefix`` (re-expansion).

        Prefix semantics match the derived-identity chain: nested
        expansions carry the outer prefix, so purging a block also
        purges its inner blocks.
        """
        for abs_path, inner in list(self.expansion_logic.items()):
            for node_id, (_node, row_prefix) in list(inner.items()):
                if row_prefix == prefix or row_prefix.startswith(
                    prefix + ".",
                ):
                    del inner[node_id]
            if not inner:
                del self.expansion_logic[abs_path]

    def _purge_anchored_rules(self, path: str) -> None:
        """Drop every rule whose ANCHOR sits at or under ``path`` (del).

        The criterion is the anchor, not the trigger: a rule of another
        row reading under the deleted subtree keeps its registration
        (its input changed, it must recompute); a rule anchored in the
        deleted subtree is dead with its row.
        """
        for abs_path, inner in list(self.expansion_logic.items()):
            for node_id, (node, _prefix) in list(inner.items()):
                anchor = node.abs_datapath(".")
                if anchor == path or anchor.startswith(path + "."):
                    del inner[node_id]
            if not inner:
                del self.expansion_logic[abs_path]

    def _execute_expansion_logic(self, path: str) -> None:
        """Run the row rules whose resolved bindings read ``path``.

        Same matching as the pointer_map: exact trigger, or a trigger
        UNDER the mutated path (a row replaced wholesale recomputes its
        rules). The compute writes re-enter the cascade like any
        canonical data-element.
        """
        seen: set[int] = set()
        grouped: dict[Any, list[SourceBagNode]] = {}
        for key, inner in self.expansion_logic.items():
            if key != path and not key.startswith(path + "."):
                continue
            for node_id, (node, _prefix) in inner.items():
                if node_id in seen:
                    continue
                seen.add(node_id)
                grouped.setdefault(node.builder, []).append(node)
        for builder, nodes in grouped.items():
            builder.compute_logic(nodes)

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
        """
        for builder, items in relevant.items():
            nodes = [
                node for _, node in items if node._get_meta("data_element")
            ]
            if nodes:
                builder.compute_logic(nodes)

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
        flush renders every builder with at least one touched node,
        toward ``target`` when given (it wins over the registered
        default for this section only).

        Requires an application and :meth:`activate` (RuntimeError
        otherwise): liveness is forbidden outside an application — a
        handler without one has no subscribes, nothing would react.

        Step one: ``_optimize_render`` is a pass-through and
        ``render_nodes`` does a full render — partial render is a later
        refinement.
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
                self._live_depth -= 1
                if self._live_depth == 0:
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

    def add_render_path(
        self, builder_name: str, path: str, kind: str = "upd",
        label: str | None = None,
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
            RenderEntry(kind, path, label),
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
        state: dict[tuple[str, str | None], str] = {}
        for kind, path, label in entries:
            key = (path, label)
            base = kind.removeprefix("row_")
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
        whole_paths = {path for path, label in state if label is None}
        kept = [
            (kind, path, label) for (path, label), kind in state.items()
            if not any(
                other != path and path.startswith(other + ".")
                for other in whole_paths
            )
            and not (label is not None and path in whole_paths)
        ]
        # Density: count surviving row entries per component path.
        row_load: dict[str, int] = {}
        for kind, path, label in kept:
            if label is not None:
                row_load[path] = row_load.get(path, 0) + 1
        coalesced = {
            path for path, count in row_load.items()
            if count > ROW_COALESCE_LIMIT
        }
        out: list[RenderEntry] = []
        for path in coalesced:
            out.append(RenderEntry("upd", path))
        for kind, path, label in kept:
            if label is not None and path in coalesced:
                continue
            if kind == "del+ins":
                row = "row_" if label is not None else ""
                out.append(RenderEntry(f"{row}del", path, label))
                out.append(RenderEntry(f"{row}ins", path, label))
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
