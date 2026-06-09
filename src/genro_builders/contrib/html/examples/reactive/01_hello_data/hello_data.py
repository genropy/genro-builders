# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Hello data, reactive: mutate the DATA and the readers re-render.

Same CustomPage as with_data/00_hello_data: an h1 reads ^message through a
pointer. Here the data behind the pointer is changed inside live sections;
the nodes that read that path re-render with the new value (data reactivity,
no data_formula / data_controller yet).
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.html.examples.reactive.example_app import ExampleApp


class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("message", "Hello Folk")

    def main(self, root):
        root.body().h1("^message")


class CustomApp(ExampleApp):
    def change_00_set_message(self, source, data):
        data.set_item("main.message", "Changed once")

    def change_01_set_message_again(self, source, data):
        data.set_item("main.message", "Changed twice")


if __name__ == "__main__":
    app = CustomApp((CustomPage(), "output.html"))
    print(app.page.rendered_target)
    app.run()
