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

from typing import Any

from genro_bag import Bag

from .source_bag import SourceBagNode


class BuilderHandler:
    """Data source for mounted builders. One segmented ``_dataroot``."""

    def __init__(self) -> None:
        self.builders: dict[str, Any] = {}
        self.application: Any = None
        self._dataroot: Bag = Bag()
        self._dataroot["_"] = Bag()        # shared/common segment
        self._dataroot.set_backref()
        # Read-time pointer tracking: key = absolute data path, value =
        # {id(node): node}. Populated by _register_path during render.
        self.pointer_map: dict[str, dict[int, SourceBagNode]] = {}
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
        """Mount one or more builders by name (name = data segment).

        Each builder is registered, given its own segment in the
        ``_dataroot``, and plugged with ``handler`` (this) and ``data``
        (its segment bag), so its pointers resolve against that segment.
        """
        for name, instance in builders.items():
            self.builders[name] = instance
            self._dataroot[name] = Bag()
            instance.handler = self
            instance.data = self._dataroot[name]
            # The handler is unique for the whole document; put it on the
            # source root so every node (host or sub-builder) reaches it
            # via the ``handler`` property (Bag.root).
            instance._sourceroot._handler = self

    def _register_path(self, node: SourceBagNode, abs_path: str) -> None:
        """Register ``node`` as a reader of ``abs_path`` (read-time tracking).

        No-op without an application: the pointer_map only feeds the
        reactive cascade, so a one-shot render need not pay for it.
        """
        if not self.application:
            return
        self.pointer_map.setdefault(abs_path, {})[id(node)] = node
