# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ExampleApp — the shared Application for the reactive examples.

A reactive example reuses the page of a non-reactive one, mounts it on a
handler, renders once, then mutates the source inside ``with app.live():``.
The Application is what makes the handler reactive (it sets itself as the
handler's ``application``); exiting a live section re-renders.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler


class ExampleApp:
    """Minimal Application: owns one reactive handler for one or more pages."""

    def __init__(self, *pages):
        self.handler = BuilderHandler(application=self)   # reactive by default
        # each item is (page, target); the page carries its own mount name
        # (passed at construction, default the dialect typology).
        for page, target in pages:
            page.set_render_target(target)
        self.handler.add_builder(*[page for page, _ in pages])
        self.handler.activate()                  # render all, then subscribe
        self.pages = list(self.handler.builders.values())
        self.page = self.pages[0]                # first page (single-page convenience)

    def source(self, name=None):
        """Return the source of a mounted builder (default: the first one)."""
        name = name or self.handler.default_builder_name
        return self.handler.builders[name].source

    def data(self):
        """Return the whole segmented datastore.

        Data is global to the handler, not per-builder: a write can affect
        nodes of several builders (via the pointer_map), so the change gets
        the full datastore and writes with an absolute path (e.g.
        ``data.set_item("main.message", ...)``).
        """
        return self.handler.data

    def live(self):
        """Open a live section on the owned handler."""
        return self.handler.live()

    def run(self):
        """Run each ``change_*`` method, one per live section, in order.

        A subclass declares numbered ``change_NN_*(self, source, data)``
        methods that mutate the source and/or the data; each runs inside its
        own ``with self.live():`` and the document is printed after the
        section closes.
        """
        for name in dir(self):
            if name.startswith("change_"):
                with self.live():
                    getattr(self, name)(self.source(), self.data())
                for page in self.pages:
                    print(page.rendered_target)
