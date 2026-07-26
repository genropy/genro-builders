# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderHandler — supplies data to the mounted builder.

A page is a builder; a builder that reads pointers (``^``/``=``) needs a
data source. The BuilderHandler is that source: it owns the ``_dataroot``
Bag and mounts ONE builder on it. It is NOT subclassed for behaviour
(only ``setup`` is an override point) and NOT a render engine — rendering
lives on the builder (create/render). The handler provides the data and,
at read time, tracks which nodes read which paths.

    handler = BuilderHandler()
    handler.add_builder(page)    # page.data IS the store

The store is FLAT: one builder, one datastore, absolute paths with no
leading segment (``counter``, not ``page.counter``). Fine reactivity is
not here — it is refounded on a compiled bag emitted by a ``livehtml``
render mode, so this handler carries no render queue, no rule engine and
no patch protocol. What survives of reactivity is the ``pointer_map``:
who reads what, populated at read time and paid for only when an
Application is present.
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag

from .source_bag import SourceBag, SourceBagNode


class BuilderHandler:
    """Data source for the mounted builder. One flat ``_dataroot``."""

    def __init__(self, application: Any = None) -> None:
        self.builder: Any = None
        self.application: Any = application
        self._dataroot: Bag = Bag()
        self._dataroot.set_backref()
        # Read-time pointer tracking: key = absolute data path, value =
        # {id(node): node}. Populated by _register_path during render.
        self.pointer_map: dict[str, dict[int, SourceBagNode]] = {}
        self.setup(self._dataroot)

    @property
    def data(self) -> Bag:
        """The datastore (one ``_dataroot`` per document)."""
        return self._dataroot

    def setup(self, data: Any) -> None:
        """Override point: seed the datastore.

        Receives the data bag, before any builder is mounted. Default
        no-op — a custom handler overrides it to seed data the builder
        reads through pointers.
        """

    def add_builder(self, builder: Any) -> None:
        """Mount ``builder`` on this handler's datastore and create it.

        The builder is plugged with ``handler`` (this) and ``data`` (the
        store, whole — there is no per-builder segment), the handler is put
        on the source root so every node reaches it via the ``handler``
        property, and the builder is created (``setup`` + ``main`` + first
        calculation, which seeds the dataSetters). ``create`` arms the
        source subscribe when reactive.
        """
        if self.builder is not None:
            raise ValueError(
                f"a builder is already mounted ({self.builder.name!r}): one "
                "handler drives one builder",
            )
        if not builder.name:
            raise ValueError(
                f"{type(builder).__name__} has no name: pass one at "
                "construction or declare a dialect _name",
            )
        self.builder = builder
        builder.handler = self
        builder.data = self._dataroot
        # The handler is unique for the whole document; put it on the
        # source root so every node (host or sub-builder) reaches it via
        # the ``handler`` property (Bag.root).
        builder._sourceroot._handler = self
        builder.create()

    def _register_path(self, node: SourceBagNode, abs_path: str) -> None:
        """Register ``node`` as a reader of ``abs_path`` (read-time tracking).

        No-op without an application: the pointer_map only feeds a reactive
        consumer, so a one-shot render need not pay for it.
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
