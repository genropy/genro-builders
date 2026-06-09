# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderHandler — supplies data to mounted builders.

A page is a builder; a builder that reads pointers (``^``/``=``) needs a
data source. The BuilderHandler is that source: it owns a single segmented
``_dataroot`` and mounts builders by name, handing each one its own data
segment. It is NOT subclassed and NOT a render engine — rendering lives
on the builder (create/render). The handler only provides the data and
(at read time) tracks which nodes read which paths.

    handler = BuilderHandler()
    handler.add_builder(main=page)   # segment "main"; page.data is its bag

The ``_`` segment is created up front as the shared/common space.
"""
from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from genro_bag import Bag

from .source_bag import SourceBag, SourceBagNode


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
        # RX livello 0 — flag di abilitazione reattività: acceso dal PRIMO
        # render (non da create()). Segna che l'avviamento è finito: la
        # pointer_map è popolata (lettura a render time) e live() è permesso.
        # live() lo esige (DR5): una pagina non resa non è reattiva.
        self._live_enabled: bool = False
        # RX livello 0 — stato della sezione live (DR4/DR6/DR7). Privati,
        # non parte dell'API: l'unico accesso pubblico è il context
        # manager live(). Il lock serializza le sezioni (sync, re-entry).
        self._live_target: Any = None
        self._live_active: bool = False
        self._live_lock: threading.RLock = threading.RLock()
        # End-of-live render queue: builder name -> touched source nodes.
        self._nodes_to_render: dict[str, list] = {}
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

    def add_builder(self, **builders: Any) -> None:
        """Mount builders by name (name = data segment) and create each.

        Each builder is registered, given its own segment in the
        ``_dataroot``, plugged with ``handler`` (this) and ``data`` (its
        segment bag), and created (``setup`` + ``main`` + first calculation,
        which seeds the data_setters). ``create`` arms the source subscribe
        when reactive; the data subscribe is armed later by :meth:`activate`,
        after the first render has populated the pointer_map.
        """
        for name, instance in builders.items():
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
        each builder's ``create``. No-op without an application.
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

    def _on_data_event(
        self, node: SourceBagNode, evt: str, pathlist: list[str], **kw: Any,
    ) -> None:
        """A data mutation recomputes the dependent logic, then queues renders.

        Derives the changed data path (ins/del: pathlist + the node's label;
        upd: the pathlist itself), collects the readers grouped by builder via
        :meth:`_relevant_nodes`, runs :meth:`execute_logic` (data_formula /
        data_controller recompute, whose writes re-enter here and cascade),
        then queues the ``node`` readers for the end-of-live render. ``node``
        is a reader of exactly the mutated datum; ``container`` / ``child``
        come later.
        """
        if evt in ("ins", "del"):
            path = ".".join([*pathlist, node.label])
        else:
            path = ".".join(pathlist)
        relevant = self._relevant_nodes(path)
        self.execute_logic(relevant)
        for builder, items in relevant.items():
            for kind, view_node in items:
                if kind == "node":
                    self.add_render_path(
                        view_node.root_builder_name, view_node.fullpath,
                    )

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
        """Open a section that batches mutations and renders on exit.

        Entering resets the render queue and marks the section active. Each
        source mutation (handled on the builder) records its touched path
        via :meth:`add_render_path`. On exit, every builder with at least
        one touched node is rendered: the queued nodes pass through
        :meth:`_optimize_render` and then ``builder.render_nodes(...)``.

        Step one: ``_optimize_render`` is a pass-through and
        ``render_nodes`` does a full render — partial render is a later
        refinement. The lock is held by the Application around this section,
        not here.
        """
        self._nodes_to_render = {}
        self._live_active = True
        self._live_target = target
        try:
            yield self
        finally:
            self._live_active = False
            for name, nodes in self._nodes_to_render.items():
                if nodes:
                    self.builders[name].render_nodes(self._optimize_render(nodes))

    def add_render_path(self, builder_name: str, path: str) -> None:
        """Record a touched path for the end-of-live render.

        ``builder_name`` is the segment the path belongs to; ``path`` is the
        path inside that builder. A source event queues the changed node's
        path (container for ins/del, the node for upd); a data event queues
        each reader's path. The end-of-live flush renders every builder
        whose queue is non-empty.
        """
        self._nodes_to_render.setdefault(builder_name, []).append(path)

    def _optimize_render(self, nodes: list) -> list:
        """Reduce the touched nodes to the minimal render set.

        Step one: pass-through (returns ``nodes`` unchanged). A later
        refinement drops nodes covered by a queued ancestor and dedupes.
        """
        return nodes

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
