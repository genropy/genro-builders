# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Didactic mini collection — the component/container mechanics.

NOT a product widget kit: the effective collections (typed input
widgets, border/tab containers, client bindings) live in genro-ws-web.
These few pieces demonstrate the two CMP citizens on the smallest
possible surface:

- ``@component`` (closed): the name in the source is the contract
  (CMP.1); a reactive kwarg-pointer passes through to the inner
  element (CMP.4), so the piece both displays and carries its
  write-back address.
- ``@container`` (fillable): the call generates REAL source nodes —
  with identity — and returns a pane the CALLER fills (CMP.9).

Usage::

    class Page(HtmlBuilder, DemoComponents, DemoContainers):
        def main(self, root):
            body = root.body()
            body.labeled_input(label="Name", value="^.name")
            card = body.card(title="People")
            card.p("Anna, Marco, Sara")
"""
from __future__ import annotations

from genro_builders.builder import component, container


class DemoComponents:
    """Two closed components. Mix into an HtmlBuilder."""

    @component
    def labeled_input(self, root, label="", value=None, **attrs):
        box = root.div(class_="demo-field", display="flex",
                       flex_direction="column", gap="4px")
        # html_label: the dialect-prefix escape — ``label`` is BagNode
        # API, the bare name never reaches the grammar from a node.
        box.html_label(label, class_="demo-field-label")
        box.input(value=value, **attrs)

    @component
    def swatch(self, root, color=None, **attrs):
        root.div(class_="demo-swatch", background=color,
                 width="48px", height="24px",
                 border="1px solid #c8c8c8", **attrs)


class DemoContainers:
    """One fillable container. Mix into an HtmlBuilder."""

    @container
    def card(self, pane, title="", **attrs):
        box = pane.div(class_="demo-card", border="1px solid #c8c8c8",
                       border_radius="6px", **attrs)
        box.div(title, class_="demo-card-title", padding="6px 8px",
                background="#f7f7f7", font_weight="600")
        return box.div(class_="demo-card-body", padding="8px")
