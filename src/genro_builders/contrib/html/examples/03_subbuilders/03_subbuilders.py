# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""03 — Sub-builders: composing HTML with SVG (and HTML again).

What you learn:
    - Switch dialect mid-document with ``@subbuilder``: from inside an
      ``HtmlBuilderHandler`` call ``body.svg()`` and continue building
      with the SVG grammar.
    - Re-enter HTML inside SVG with ``svg.html(...).div(...)``: the
      framework wraps the HTML subtree in ``<foreignObject>`` with the
      xhtml namespace at render time. The user writes only ``html``.
    - Mix dialects freely: HTML host owns the page, SVG owns vector
      shapes, HTML inside SVG owns rich-text overlays.
    - Inspect how the framework realises this: the schema entry for
      ``svg`` carries ``is_subbuilder=True`` and the live node carries
      the correct builder on its ``_builder`` slot.

Prerequisites: 01_introduction, 02_inline_styling.

Usage:
    python 03_subbuilders.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder, HtmlBuilderHandler

# ---------------------------------------------------------------------------
# 1. HTML hosting SVG: a single shape inline
# ---------------------------------------------------------------------------


class Section1(HtmlBuilderHandler):
    """A red circle and a blue rectangle sitting inside an HTML body.

    Note how ``body.svg(...)`` opens the SVG dialect: from there on
    ``rect``, ``circle`` are valid (they belong to SVG, not HTML).
    """

    def main(self, root):
        body = root.body()
        body.h2("Two shapes inline")
        s = body.svg(width=200, height=80, viewBox="0 0 200 80")
        s.circle(cx=40, cy=40, r=30, fill="#e74c3c")
        s.rect(x=90, y=20, width=90, height=40, fill="#3498db")


# ---------------------------------------------------------------------------
# 2. A small composable SVG icon (HTML host, SVG subtree)
# ---------------------------------------------------------------------------


class Section2(HtmlBuilderHandler):
    """A "status badge": an SVG icon next to an HTML label, all in one
    flow. The icon uses an ``<svg>`` with a coloured background, a
    centred circle and a checkmark drawn as a ``<path>``."""

    def main(self, root):
        body = root.body(display="flex", align_items="center", gap="12px")
        # Icon: a green disc with a white check mark.
        s = body.svg(width=32, height=32, viewBox="0 0 32 32")
        s.circle(cx=16, cy=16, r=15, fill="#27ae60")
        s.path(
            d="M9 16 l5 5 l9 -10",
            stroke="white", stroke_width=3, fill="none",
            stroke_linecap="round", stroke_linejoin="round",
        )
        body.span("Online", color="#27ae60", font_weight="600")


# ---------------------------------------------------------------------------
# 3. Several SVG primitives in one figure
# ---------------------------------------------------------------------------


class Section3(HtmlBuilderHandler):
    """A small infographic: gradient-free shapes used together. The
    point is that every shape (rect, circle, ellipse, line, polygon)
    is offered by the SVG grammar, and the host HTML page does not
    have to know about any of them."""

    def main(self, root):
        body = root.body()
        body.h2("SVG primitives in one figure")
        s = body.svg(width=360, height=160, viewBox="0 0 360 160")
        # Background panel.
        s.rect(x=0, y=0, width=360, height=160, fill="#ecf0f1")
        # A row of three circles.
        s.circle(cx=60, cy=40, r=24, fill="#1abc9c")
        s.circle(cx=130, cy=40, r=24, fill="#3498db")
        s.circle(cx=200, cy=40, r=24, fill="#9b59b6")
        # An ellipse and a line.
        s.ellipse(cx=300, cy=40, rx=40, ry=20, fill="#e67e22")
        s.line(x1=20, y1=90, x2=340, y2=90, stroke="#34495e", stroke_width=2)
        # A polygon (triangle).
        s.polygon(points="60,150 100,110 140,150", fill="#e74c3c")
        # A piece of inline text.
        s.text("inline SVG", x=170, y=140, font_size=14, fill="#2c3e50")


# ---------------------------------------------------------------------------
# 4. SVG hosting HTML via ``svg.html(...)``
# ---------------------------------------------------------------------------


class Section4(HtmlBuilderHandler):
    """Inside an SVG drawing, place rich HTML content (paragraphs, lists,
    styled text) without leaving the page flow.

    The user writes ``s.html()`` — the framework wraps the HTML subtree
    in ``<foreignObject xmlns="http://www.w3.org/1999/xhtml">`` at
    render time. The bare ``html`` tag never appears in the output."""

    def main(self, root):
        body = root.body()
        body.h2("HTML overlay inside SVG")
        s = body.svg(width=360, height=180, viewBox="0 0 360 180")
        # Background card.
        s.rect(x=0, y=0, width=360, height=180, rx=12, ry=12, fill="#2c3e50")
        # Decorative circle.
        s.circle(cx=40, cy=40, r=20, fill="#f1c40f")
        # The HTML overlay: framework wraps it in <foreignObject>.
        overlay = s.html(x=80, y=20, width=260, height=140)
        card = overlay.div(
            color="white", font_family="sans-serif", padding="8px",
        )
        card.div("Mixed content", font_weight="700", font_size="16px")
        card.p(
            "This block is HTML rendered inside an SVG, ideal for "
            "long-form copy that SVG <text> cannot wrap natively.",
            font_size="13px", margin="6px 0 0 0",
        )


# ---------------------------------------------------------------------------
# 5. Triple switch — HTML page + SVG chart + HTML caption inside SVG
# ---------------------------------------------------------------------------


class Section5(HtmlBuilderHandler):
    """A miniature "dashboard card": HTML title and footer, SVG bar
    chart in the middle, and inside the chart a small HTML caption
    via the ``svg.html()`` re-entry. Three dialect switches in one
    coherent piece of markup."""

    def main(self, root):
        body = root.body(
            font_family="sans-serif", color="#2c3e50",
        )
        # Outer card.
        card = body.div(
            background="white", padding="16px",
            border="1px solid #bdc3c7", border_radius=8,
            width="360px",
        )
        card.h3("Q1 sales", margin="0 0 8px 0")
        # SVG chart.
        chart = card.svg(width=320, height=140, viewBox="0 0 320 140")
        bars = [("Jan", 80, "#3498db"), ("Feb", 60, "#9b59b6"),
                ("Mar", 100, "#e67e22"), ("Apr", 45, "#1abc9c")]
        x = 10
        for label, h, color in bars:
            chart.rect(x=x, y=120 - h, width=60, height=h, fill=color)
            chart.text(label, x=x + 30, y=135,
                       font_size=11, text_anchor="middle", fill="#2c3e50")
            x += 80
        # HTML caption *inside* SVG, anchored top-right via foreignObject.
        cap = chart.html(x=200, y=4, width=110, height=22)
        cap.div(
            "↑ Apr below target",
            color="#e74c3c", font_size="11px", font_weight="600",
            text_align="right",
        )
        # HTML footer outside SVG, resumes naturally.
        card.p(
            "Source: internal forecast",
            font_size="11px", color="#7f8c8d", margin="8px 0 0 0",
        )


# ---------------------------------------------------------------------------
# 6. Inspection: how the framework knows
# ---------------------------------------------------------------------------


class Section6(HtmlBuilderHandler):
    """Render-side example for the framework introspection cell.

    This handler exists only so the inspection snippet has something
    to walk: ``body.svg().rect(...)``. The interesting content of
    Section 6 lives in the notebook narrative cell (schema lookup +
    node._builder check)."""

    def main(self, root):
        body = root.body()
        body.svg(width=120, height=40).rect(
            x=0, y=0, width=120, height=40, fill="#16a085",
        )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _render_section(handler_cls, *, pretty=True):
    page = handler_cls()
    page.create()
    return page.render(pretty=pretty)


if __name__ == "__main__":
    sections = [Section1, Section2, Section3, Section4, Section5, Section6]
    parts = []
    for i, cls in enumerate(sections, 1):
        parts.append(f"<!-- Section {i} -->")
        parts.append(_render_section(cls))
        parts.append("")
    rendered = "\n".join(parts)

    # Bonus: show how the framework realises sub-builders.
    info = HtmlBuilder()._get_schema_info("svg")
    inspection = (
        f"\n<!-- Inspection -->\n"
        f"<!-- HtmlBuilder._get_schema_info('svg'):\n"
        f"     is_subbuilder={info.get('is_subbuilder')}, "
        f"subbuilder_name={info.get('subbuilder_name')!r} -->\n"
    )
    rendered += inspection

    output = Path(__file__).with_suffix(".html")
    output.write_text(rendered)
    print(rendered)
    print(f"Saved to {output}")
