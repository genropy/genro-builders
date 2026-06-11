# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlComponentsBase — the first widget collection (closed components).

Input widgets named after the WIDGET, not the HTML type (legacy
flavor): ``textbox``, ``colorpicker``, ``datepicker``, ... Each one is
a ``@component``: self-contained, parameterized by the caller, the
name in the source is the cross-runtime contract (CMP.1). A reactive
``value`` pointer passes through to the inner ``<input>`` (CMP.4), so
the widget both displays AND writes back.

``labeled_field`` composes a widget with its label inside a bordered
box (component-in-component, CMP.8). Styling is inline-minimal with
class hooks (``gnr-field``, ``gnr-field-label``) for CSS overrides;
the collection will carry its own stylesheet when ``cssrequires``
(CMP.6) lands.

Usage::

    class Page(HtmlBuilder, HtmlComponentsBase):
        def main(self, root):
            root.labeled_field(label="Born", kind="datepicker",
                               value="^.born", border=True, rounded=True)

Fillable containers (border/tab/stack) are the OTHER citizen
(``@container``) and live elsewhere.
"""
from __future__ import annotations

from genro_builders.builder import component


class HtmlComponentsBase:
    """Closed input widgets as components. Mix into an HtmlBuilder."""

    # ------------------------------------------------------------------
    # Input variants — one widget per UX, value rides the pointer
    # ------------------------------------------------------------------

    @component
    def textbox(self, root, value=None, **attrs):
        root.input(html_type="text", value=value, **attrs)

    @component
    def passwordbox(self, root, value=None, **attrs):
        root.input(html_type="password", value=value, **attrs)

    @component
    def colorpicker(self, root, value=None, **attrs):
        root.input(html_type="color", value=value, **attrs)

    @component
    def datepicker(self, root, value=None, **attrs):
        root.input(html_type="date", value=value, **attrs)

    @component
    def timepicker(self, root, value=None, **attrs):
        root.input(html_type="time", value=value, **attrs)

    @component
    def numberbox(self, root, value=None, **attrs):
        root.input(html_type="number", value=value, **attrs)

    @component
    def slider(self, root, value=None, **attrs):
        root.input(html_type="range", value=value, **attrs)

    @component
    def checkbox(self, root, value=None, **attrs):
        # A checkbox state is its ``checked`` attribute (boolean by
        # presence); the value pointer rides it, the client reads
        # ``el.checked`` on write-back.
        root.input(html_type="checkbox", checked=value, **attrs)

    # ------------------------------------------------------------------
    # labeled_field — label + widget in a bordered box
    # ------------------------------------------------------------------

    @component
    def labeled_field(self, root, label="", kind="textbox", value=None,
                      label_position="top", border=True, rounded=False,
                      **attrs):
        """A widget with its label: ``top`` (above, left-aligned) or
        ``left`` (inline). ``kind`` names any widget of the collection;
        ``value`` and the extra attrs reach the inner input."""
        box_style = {
            "display": "flex",
            "gap": "4px" if label_position == "top" else "8px",
            "flex_direction": "column" if label_position == "top" else "row",
        }
        if label_position == "left":
            box_style["align_items"] = "center"
        if border:
            # The color rides a CSS variable so a class rule can recolor
            # the border on :focus-within despite the inline style.
            box_style["border"] = "1px solid var(--gnr-field-border, #c8c8c8)"
            box_style["padding"] = "6px 8px"
        if rounded:
            box_style["border_radius"] = "6px"
        box = root.div(class_="gnr-field", **box_style)
        # html_label: the dialect-prefix escape — ``label`` is BagNode
        # API, the bare name never reaches the grammar from a node.
        box.html_label(label, class_="gnr-field-label")
        getattr(box, kind)(value=value, **attrs)
