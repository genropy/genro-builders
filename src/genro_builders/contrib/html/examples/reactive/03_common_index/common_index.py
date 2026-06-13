# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""03 — Common index, reactive: one shared datum read by three pages.

Three pages are mounted on one handler. The shared ``_`` segment holds a
single ``index`` (seeded by a dataSetter on the common volume, ``_:index``);
each page shows it through ``^_:index``. Changing ``_.index`` inside a live
section re-renders the readers of all three pages — one datum, many builders.
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.html.examples.reactive.example_app import ExampleApp


class PageOne(HtmlBuilder):
    def main(self, root):
        root.dataSetter(destination="_:index", value=0)
        root.body().div("^_:index")


class PageTwo(HtmlBuilder):
    def main(self, root):
        root.body().div("^_:index")


class PageThree(HtmlBuilder):
    def main(self, root):
        root.body().div("^_:index")


class CustomApp(ExampleApp):
    def change_00_set_index(self, source, data):
        data.set_item("_.index", 1)

    def change_01_set_index_again(self, source, data):
        data.set_item("_.index", 2)


if __name__ == "__main__":
    app = CustomApp(
        (PageOne(name="page1"), "page1.html"),
        (PageTwo(name="page2"), "page2.html"),
        (PageThree(name="page3"), "page3.html"),
    )
    for page in app.pages:
        print(page.rendered_target)
    app.run()
