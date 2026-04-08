# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Iterate example — data-driven SVG badges from a Bag of people.

Demonstrates the ``iterate`` feature: a single @component describes
one badge, and ``iterate='^people'`` replicates it for every child
in the data bag.  Each instance resolves ``^.?name``, ``^.?role``,
``^.?color`` against the attributes of its own data node.

Usage:
    python -m genro_builders.contrib.svg.examples.iterate_example
"""

from __future__ import annotations

from pathlib import Path

from genro_bag import Bag

from genro_builders.builder import component
from genro_builders.contrib.svg import SvgBuilder
from genro_builders.manager import BuilderManager

BADGE_H = 60
BADGE_W = 260
GAP = 10


class BadgeBuilder(SvgBuilder):
    """SvgBuilder extended with a badge component."""

    @component(sub_tags='')
    def badge(self, comp, **kwargs):
        """One rounded badge: colored strip + name + role."""
        comp.rect(
            x="0", y="0", width=str(BADGE_W), height=str(BADGE_H),
            rx="8", fill="white", stroke="#ccc", stroke_width="1",
        )
        comp.rect(
            x="0", y="0", width="8", height=str(BADGE_H),
            rx="4", fill="^.?color",
        )
        comp.text(
            "^.?name", x="24", y="28",
            font_size="18", font_weight="bold", fill="#333",
        )
        comp.text(
            "^.?role", x="24", y="48",
            font_size="13", fill="#888",
        )


class BadgeSheet(BuilderManager):
    """Manager that builds a sheet of badges from data."""

    def __init__(self):
        self.page = self.set_builder("page", BadgeBuilder)

    def store(self, data):
        people = Bag()
        people.set_item("p0", None,
                        name="Alice Rossi", role="Lead Developer", color="#3498db")
        people.set_item("p1", None,
                        name="Marco Verdi", role="UX Designer", color="#2ecc71")
        people.set_item("p2", None,
                        name="Sara Bianchi", role="Project Manager", color="#e74c3c")
        people.set_item("p3", None,
                        name="Luca Neri", role="Backend Engineer", color="#9b59b6")
        data["people"] = people

    def main(self, source):
        n_people = len(self.reactive_store["people"])
        total_h = n_people * (BADGE_H + GAP) + GAP

        svg = source.svg(
            width=str(BADGE_W + 2 * GAP),
            height=str(total_h),
            viewBox=f"0 0 {BADGE_W + 2 * GAP} {total_h}",
            xmlns="http://www.w3.org/2000/svg",
        )

        # iterate replicates badge() for each child of ^people
        svg.badge(iterate="^people")


def demo():
    """Build and save the badge sheet."""
    app = BadgeSheet()
    app.run(subscribe=False)

    output = app.page.render()
    print(output)

    output_dir = Path(__file__).parent.parent.parent.parent.parent / "temp"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "badge_sheet.svg"
    path.write_text(output)
    print(f"\nSaved to {path}")


if __name__ == "__main__":
    demo()
