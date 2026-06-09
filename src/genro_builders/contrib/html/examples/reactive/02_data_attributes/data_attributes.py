# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""02 — Data attributes, reactive: change the data, the reader re-renders.

A data_setter seeds ``name`` with a value and attributes; a div reads the
value (^name) and the attributes (^name?color, ^name?background). Inside a
live section the data is changed and the nodes that read it re-render.
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.html.examples.reactive.example_app import ExampleApp


class CustomPage(HtmlBuilder):
    def main(self, root):
        root.data_setter(
            destination="name", value="John", color="red", background="yellow",
        )
        root.body().div(
            "^name", color="^name?color", background="^name?background",
        )


class CustomApp(ExampleApp):
    def change_00_name(self, source, data):
        data.set_item("main.name", "Martin")


if __name__ == "__main__":
    app = CustomApp((CustomPage(), "output.html"))
    print(app.page.rendered_target)
    app.run()
