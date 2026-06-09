# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Styled demo: a document that carries its own CSS via an inline ``<style>``.

Shows ``<style>`` written with the builder (allowed in the body since the
grammar treats it as flow content) and rendered as a raw text element, so
CSS combinators like ``h1 > span`` survive unescaped. The page is fully
self-contained: no external stylesheet, the look travels with the markup.
"""

from __future__ import annotations

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "Styled (inline CSS)"

_CSS = """
.card {
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  margin: 0.75rem 0;
  background: #fafafa;
}
.card > h2 {
  margin: 0 0 0.5rem;
  color: #2c5f8a;
}
.card > p {
  margin: 0;
  color: #555;
}
.tag {
  display: inline-block;
  font-size: 0.75rem;
  background: #2c5f8a;
  color: white;
  border-radius: 4px;
  padding: 0.1rem 0.5rem;
}
"""


class Demo(InteractiveDemo):
    """A card styled by an inline ``<style>`` block, no external CSS.

    Data lives under ``page``: ``page.title``, ``page.body``.
    """

    def setup(self, data):
        self.set_data("page.title", "Self-contained card")
        self.set_data("page.body", "This page carries its own CSS.")

    def main(self, root):
        body = root.body(datapath="page")
        body.style(_CSS)
        card = body.div(class_="card")
        card.h2("^.title")
        card.p("^.body")
        card.span("inline style", class_="tag")


if __name__ == "__main__":
    demo = Demo()
    demo.create()
    print(demo.render())
