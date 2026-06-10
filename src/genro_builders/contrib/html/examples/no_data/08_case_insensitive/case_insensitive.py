# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""08 — Case-insensitive tags: ``div``, ``Div``, ``DIV`` are one element.

Tag dispatch ignores case but is underscore-sensitive: ``div``/``Div``/
``DIV`` all resolve to the same ``<div>`` element. The emitted tag keeps
the case the grammar declared (so SVG's ``linearGradient`` stays camelCase
on the wire whether you call ``linearGradient`` or ``lineargradient``).
Attribute names, on the other hand, are case-sensitive: ``id`` and ``ID``
are two distinct attributes.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def main(self, root):
        body = root.body()
        # Same element three ways — all emit <div>.
        body.div("lower")
        body.Div("upper")
        body.DIV("mixed")
        # Attribute names ARE case-sensitive: two distinct attributes.
        body.span(id="lowercase", ID="uppercase")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
