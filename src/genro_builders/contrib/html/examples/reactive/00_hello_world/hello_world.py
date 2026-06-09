# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""00 — Hello world, reactive: the same page, mutated inside live sections.

Same CustomPage as no_data/00_hello_world. CustomApp subclasses ExampleApp
and declares one numbered ``change_NN_*`` method per mutation; ``run()``
executes each inside its own ``with self.live():``, hands it the source,
and prints the document after every section. The body is reached by its
stable label (``source['body']``) — no node_id needed.
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.html.examples.reactive.example_app import ExampleApp


class CustomPage(HtmlBuilder):
    def main(self, root):
        body = root.body()
        body.h1("Hello World")
        body.p("My first page with genro-builders.")


class CustomApp(ExampleApp):
    def change_00_add_one_div(self, source, data):
        source["body"].div("one div")

    def change_01_remove_the_div(self, source, data):
        source["body"].del_item("div_0")

    def change_02_add_four_divs(self, source, data):
        body = source["body"]
        for i in range(4):
            body.div(f"div {i}")

    def change_03_add_div_at_position_four(self, source, data):
        source["body"].div("at four", node_position=4)

    def change_04_remove_three_divs(self, source, data):
        body = source["body"]
        divs = [node.label for node in body if node.node_tag == "div"]
        for label in divs[:3]:
            body.del_item(label)

    def change_05_inject_block_wrapped(self, source, data):
        # The prepared block becomes the content of a new <div> wrapper.
        block = self.page.new_root()
        block.div("prepared", class_="card")
        block.p("inside the block")
        source["body"].div(block)

    def change_06_inject_block_merged(self, source, data):
        # The prepared block's nodes are merged straight into the body
        # (no wrapper); update() fires an 'ins' per node, so it is reactive.
        # CAVEAT: update() merges by label — a block node whose label already
        # exists in the body (e.g. an auto 'p_0') OVERWRITES the existing one.
        # An additive merge that re-labels to avoid collisions is a nice-to-have.
        block = self.page.new_root()
        block.div("merged", class_="card")
        block.p("merged in place")
        source["body"].update(block)

    def change_07_set_existing_div(self, source, data):
        # An explicit node_label that already exists is an UPDATE, not an
        # insert: the value of div_0 is rewritten (no new node).
        source["body"].div("check set", node_label="div_0")

    def change_08_set_only_attributes(self, source, data):
        # Same label, only attributes, no value: the attribute is set and the
        # value is reset to None (no value passed -> the node is rewritten).
        source["body"].div(node_label="div_0", class_="hot")


if __name__ == "__main__":
    app = CustomApp(CustomPage(), "output.html")
    print(app.page.rendered_target)
    app.run()
