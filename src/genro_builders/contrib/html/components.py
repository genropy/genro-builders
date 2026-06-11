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

#: dtype -> widget kind: the SAME map the future ``field`` derivator
#: will use (legacy ``wdgAttributesFromColumn`` parity). DH/DHZ will
#: join when the datetimepicker lands.
DTYPE_KINDS = {
    "A": "textbox", "T": "textbox",
    "B": "checkbox",
    "L": "numberbox", "I": "numberbox",
    "R": "numberbox", "N": "numberbox",
    "D": "datepicker",
    "H": "timepicker",
}


class HtmlComponentsBase:
    """Closed input widgets as components. Mix into an HtmlBuilder."""

    # ------------------------------------------------------------------
    # Input variants — one widget per UX, value rides the pointer.
    # Each widget knows its native dtype (the legacy wrappers stamp it
    # on every write: DateTextBox._dtype='D' and friends): the render
    # emits it as ``data-dtype``, the client sends value and dtype as
    # separate mutate parameters, the server types the write (TYTX).
    # ------------------------------------------------------------------

    def _input(self, root, html_type, value=None, dtype=None, ghost=None,
               **attrs):
        """Shared input emission: data-dtype + ghost->placeholder."""
        if dtype:
            attrs["data-dtype"] = dtype
        if ghost is not None:
            attrs["placeholder"] = ghost
        root.input(html_type=html_type, value=value, **attrs)

    @component
    def textbox(self, root, value=None, dtype=None, ghost=None, trim=True,
                **attrs):
        # Legacy parity: text trims by default; data-trim="false" is the
        # exception the client honors.
        if not trim:
            attrs["data-trim"] = "false"
        self._input(root, "text", value=value, dtype=dtype, ghost=ghost,
                    **attrs)

    @component
    def passwordbox(self, root, value=None, ghost=None, **attrs):
        # Never trimmed, never typed: a password is bytes the user owns.
        self._input(root, "password", value=value, ghost=ghost, **attrs)

    @component
    def colorpicker(self, root, value=None, **attrs):
        self._input(root, "color", value=value, **attrs)

    @component
    def datepicker(self, root, value=None, dtype="D", ghost=None, **attrs):
        self._input(root, "date", value=value, dtype=dtype, ghost=ghost,
                    **attrs)

    @component
    def timepicker(self, root, value=None, dtype="H", ghost=None, **attrs):
        self._input(root, "time", value=value, dtype=dtype, ghost=ghost,
                    **attrs)

    @component
    def numberbox(self, root, value=None, dtype="N", places=None,
                  ghost=None, **attrs):
        # ``places`` drives the step (legacy: places=0 for L/I); without
        # it, integers step by 1 and decimals are free ("any").
        if places is None and dtype in ("L", "I"):
            places = 0
        if "step" not in attrs:
            if places == 0:
                attrs["step"] = "1"
            elif places:
                attrs["step"] = "0." + "0" * (places - 1) + "1"
            else:
                attrs["step"] = "any"
        self._input(root, "number", value=value, dtype=dtype, ghost=ghost,
                    **attrs)

    @component
    def slider(self, root, value=None, dtype="L", **attrs):
        self._input(root, "range", value=value, dtype=dtype, **attrs)

    @component
    def checkbox(self, root, value=None, dtype=None, label=None,
                 toggle=False, **attrs):
        """A checkbox state is its ``checked`` attribute (boolean by
        presence); the client reads ``el.checked`` on write-back —
        already typed, no dtype on the wire. ``label`` puts a caption
        beside it (``label_*`` attrs reach the caption); ``toggle``
        styles it as a switch."""
        if dtype not in (None, "B"):
            raise ValueError(f"checkbox dtype must be 'B', got {dtype!r}")
        label_attrs = {
            k[len("label_"):]: attrs.pop(k)
            for k in list(attrs) if k.startswith("label_")
        }
        if label is None:
            root.input(html_type="checkbox", checked=value, **attrs)
            return
        box = root.div(
            class_="gnr-checkbox" + (" gnr-toggle" if toggle else ""),
            display="flex", align_items="center", gap="6px",
        )
        box.input(html_type="checkbox", checked=value, **attrs)
        box.html_label(label, **label_attrs)

    # ------------------------------------------------------------------
    # labeled_field — label + widget in a bordered box
    # ------------------------------------------------------------------

    @component
    def labeled_field(self, root, label="", lbl=None, kind=None, dtype=None,
                      value=None, label_position="top", border=True,
                      rounded=False, **attrs):
        """A widget with its label: ``top`` (above, left-aligned) or
        ``left`` (inline). ``kind`` names any widget of the collection,
        or is derived from ``dtype`` (the map ``field`` will use);
        ``lbl`` is the legacy-parity alias of ``label``. ``value``,
        ``dtype`` and the extra attrs reach the inner widget."""
        if kind is None:
            if dtype is not None and dtype not in DTYPE_KINDS:
                raise ValueError(f"no widget kind for dtype {dtype!r}")
            kind = DTYPE_KINDS[dtype] if dtype else "textbox"
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
        box.html_label(label or lbl or "", class_="gnr-field-label")
        widget_kw = {"value": value, **attrs}
        if dtype is not None:
            widget_kw["dtype"] = dtype
        getattr(box, kind)(**widget_kw)
