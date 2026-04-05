# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""SVG chart examples — bar chart, target, house icon, card with shadow.

Demonstrates SvgBuilder producing real SVG output that can be
opened in any browser or embedded in HTML.

Usage:
    python -m genro_builders.contrib.svg.examples.svg_chart_example

Output — bar_chart()::

    <svg width="400" height="260" viewBox="0 0 400 260" xmlns="http://www.w3.org/2000/svg">
      <title>Monthly Sales</title>
      <defs>
        <linearGradient id="barGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#4facfe" />
          <stop offset="100%" stop-color="#00f2fe" />
        </linearGradient>
      </defs>
      <g transform="translate(80, 30)">
        <rect x="0" y="0" width="168" height="30" fill="url(#barGrad)" rx="4" />
        <text x="176" y="20" font-size="14" fill="#333">120</text>
        <text x="-10" y="20" font-size="14" fill="#666" text-anchor="end">Jan</text>
        <rect x="0" y="38" width="126" height="30" fill="url(#barGrad)" rx="4" />
        <text x="134" y="58" font-size="14" fill="#333">90</text>
        <text x="-10" y="58" font-size="14" fill="#666" text-anchor="end">Feb</text>
        <rect x="0" y="76" width="210" height="30" fill="url(#barGrad)" rx="4" />
        <text x="218" y="96" font-size="14" fill="#333">150</text>
        <text x="-10" y="96" font-size="14" fill="#666" text-anchor="end">Mar</text>
        <rect x="0" y="114" width="112" height="30" fill="url(#barGrad)" rx="4" />
        <text x="120" y="134" font-size="14" fill="#333">80</text>
        <text x="-10" y="134" font-size="14" fill="#666" text-anchor="end">Apr</text>
        <rect x="0" y="152" width="280" height="30" fill="url(#barGrad)" rx="4" />
        <text x="288" y="172" font-size="14" fill="#333">200</text>
        <text x="-10" y="172" font-size="14" fill="#666" text-anchor="end">May</text>
        <rect x="0" y="190" width="238" height="30" fill="url(#barGrad)" rx="4" />
        <text x="246" y="210" font-size="14" fill="#333">170</text>
        <text x="-10" y="210" font-size="14" fill="#666" text-anchor="end">Jun</text>
      </g>
    </svg>

Output — concentric_circles()::

    <svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
      <title>Target</title>
      <circle cx="100" cy="100" r="90" fill="#e74c3c" stroke="#c0392b" stroke-width="2" />
      <circle cx="100" cy="100" r="72" fill="#ffffff" stroke="#c0392b" stroke-width="2" />
      <circle cx="100" cy="100" r="54" fill="#e74c3c" stroke="#c0392b" stroke-width="2" />
      <circle cx="100" cy="100" r="36" fill="#ffffff" stroke="#c0392b" stroke-width="2" />
      <circle cx="100" cy="100" r="18" fill="#e74c3c" stroke="#c0392b" stroke-width="2" />
    </svg>

Output — icon_composition() (house)::

    <svg width="120" height="120" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
      <title>House Icon</title>
      <polygon points="60,10 10,60 110,60" fill="#e67e22" />
      <rect x="25" y="60" width="70" height="50" fill="#f39c12" />
      <rect x="48" y="75" width="24" height="35" fill="#8e44ad" rx="3" />
      <rect x="32" y="72" width="14" height="14" fill="#3498db" stroke="#2c3e50" stroke-width="1" />
      <rect x="74" y="72" width="14" height="14" fill="#3498db" stroke="#2c3e50" stroke-width="1" />
      <rect x="80" y="25" width="12" height="30" fill="#95a5a6" />
    </svg>

Output — filtered_shadow() (card)::

    <svg width="200" height="160" viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feOffset dx="4" dy="4" result="offsetBlur" />
          <feMerge>
            <feMergeNode in_="offsetBlur" />
            <feMergeNode in_="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect x="30" y="20" width="140" height="100" rx="8" fill="white" stroke="#ddd"
            stroke-width="1" filter="url(#shadow)" />
      <text x="100" y="60" text-anchor="middle" font-size="16" font-weight="bold"
            fill="#333">Card Title</text>
      <text x="100" y="85" text-anchor="middle" font-size="12"
            fill="#999">With drop shadow</text>
    </svg>
"""

from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.svg import SvgBuilder


def bar_chart():
    """Horizontal bar chart with gradient fill and labels."""
    builder = SvgBuilder()
    svg = builder.source.svg(
        width="400", height="260", viewBox="0 0 400 260",
        xmlns="http://www.w3.org/2000/svg",
    )

    svg.title("Monthly Sales")

    # Gradient definition
    defs = svg.defs()
    grad = defs.linearGradient(id="barGrad", x1="0", y1="0", x2="1", y2="0")
    grad.stop(offset="0%", stop_color="#4facfe")
    grad.stop(offset="100%", stop_color="#00f2fe")

    # Data
    data = [
        ("Jan", 120), ("Feb", 90), ("Mar", 150),
        ("Apr", 80), ("May", 200), ("Jun", 170),
    ]
    bar_h = 30
    gap = 8
    max_val = max(v for _, v in data)
    chart_w = 280

    # Chart group
    chart = svg.g(transform="translate(80, 30)")

    for i, (label, value) in enumerate(data):
        y = i * (bar_h + gap)
        w = int(value / max_val * chart_w)

        # Bar
        chart.rect(x="0", y=str(y), width=str(w), height=str(bar_h),
                   fill="url(#barGrad)", rx="4")

        # Value label
        chart.text(str(value), x=str(w + 8), y=str(y + 20),
                   font_size="14", fill="#333")

        # Category label
        chart.text(label, x="-10", y=str(y + 20),
                   font_size="14", fill="#666", text_anchor="end")

    builder.build()
    return builder.render()


def concentric_circles():
    """Target-like concentric circles with alternating colors."""
    builder = SvgBuilder()
    svg = builder.source.svg(
        width="200", height="200", viewBox="0 0 200 200",
        xmlns="http://www.w3.org/2000/svg",
    )

    svg.title("Target")

    colors = ["#e74c3c", "#ffffff", "#e74c3c", "#ffffff", "#e74c3c"]
    radii = [90, 72, 54, 36, 18]

    for r, color in zip(radii, colors, strict=True):
        svg.circle(cx="100", cy="100", r=str(r), fill=color,
                   stroke="#c0392b", stroke_width="2")

    builder.build()
    return builder.render()


def icon_composition():
    """Compose a simple icon using basic shapes — a house."""
    builder = SvgBuilder()
    svg = builder.source.svg(
        width="120", height="120", viewBox="0 0 120 120",
        xmlns="http://www.w3.org/2000/svg",
    )

    svg.title("House Icon")

    # Roof (triangle via polygon)
    svg.polygon(points="60,10 10,60 110,60", fill="#e67e22")

    # Wall
    svg.rect(x="25", y="60", width="70", height="50", fill="#f39c12")

    # Door
    svg.rect(x="48", y="75", width="24", height="35", fill="#8e44ad", rx="3")

    # Window left
    svg.rect(x="32", y="72", width="14", height="14", fill="#3498db",
             stroke="#2c3e50", stroke_width="1")

    # Window right
    svg.rect(x="74", y="72", width="14", height="14", fill="#3498db",
             stroke="#2c3e50", stroke_width="1")

    # Chimney
    svg.rect(x="80", y="25", width="12", height="30", fill="#95a5a6")

    builder.build()
    return builder.render()


def filtered_shadow():
    """Rectangle with drop shadow filter."""
    builder = SvgBuilder()
    svg = builder.source.svg(
        width="200", height="160", viewBox="0 0 200 160",
        xmlns="http://www.w3.org/2000/svg",
    )

    # Filter definition
    defs = svg.defs()
    f = defs.filter(id="shadow", x="-20%", y="-20%", width="140%", height="140%")
    f.feGaussianBlur(stdDeviation="4", result="blur")
    f.feOffset(dx="4", dy="4", result="offsetBlur")

    merge = f.feMerge()
    merge.feMergeNode(in_="offsetBlur")
    merge.feMergeNode(in_="SourceGraphic")

    # Card with shadow
    svg.rect(x="30", y="20", width="140", height="100", rx="8",
             fill="white", stroke="#ddd", stroke_width="1", filter="url(#shadow)")

    svg.text("Card Title", x="100", y="60",
             text_anchor="middle", font_size="16", font_weight="bold", fill="#333")
    svg.text("With drop shadow", x="100", y="85",
             text_anchor="middle", font_size="12", fill="#999")

    builder.build()
    return builder.render()


def demo():
    """Run all examples and save to files."""
    output_dir = Path(__file__).parent.parent.parent.parent.parent / "temp"
    output_dir.mkdir(exist_ok=True)

    examples = [
        ("bar_chart.svg", bar_chart),
        ("concentric_circles.svg", concentric_circles),
        ("house_icon.svg", icon_composition),
        ("card_shadow.svg", filtered_shadow),
    ]

    for filename, func in examples:
        svg_output = func()
        path = output_dir / filename
        path.write_text(svg_output)
        print(f"Saved {path}")
        print(svg_output[:200])
        print("...\n")


if __name__ == "__main__":
    demo()
