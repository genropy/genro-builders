# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""02 — Static Page: structure, nesting, and composition.

What you learn:
    - Split main() into methods for logical composition
    - Full HTML structure: head + body
    - Nesting: div > h2 + ul > li
    - Attributes: _class (maps to class), id, href
    - Python methods = reusable building blocks
    - FileResolver: load CSS from external file (lazy, on-demand)

Genro ecosystem note:
    ``FileResolver`` (from genro-bag) is a resolver — a pull-based
    mechanism where the value is computed/loaded on first access.
    When you write ``head.style(FileResolver('style.css'))``, the CSS
    file is NOT read immediately. It is read at render time, when the
    node's value is needed. If the file changes between renders, the
    next render picks up the new version. This is the same pull model
    used by ``data_formula`` for computed values.

Prerequisites: 01_hello_world

Usage:
    python 02_static_page.py
"""
from __future__ import annotations

from pathlib import Path

from genro_bag.resolvers import FileResolver

from genro_builders.contrib.html import HtmlManager

HERE = Path(__file__).parent


class StaticPage(HtmlManager):
    """A static page composed from logical building blocks."""

    def main(self, source):
        self.page_head(source)
        body = source.body()
        page = body.div(_class="page")
        self.hero(page)
        self.navigation(page)
        self.features(page)
        page.footer().p("Built with genro-builders.")

    def page_head(self, source):
        head = source.head()
        head.meta(charset="utf-8")
        head.title("My Static Page")
        # FileResolver reads the CSS file lazily at render time.
        # If style.css changes, the next render picks up the new version.
        head.style(FileResolver("style.css", base_path=str(HERE)))

    def hero(self, body):
        hero = body.div(_class="hero")
        hero.h1("Welcome to GenroBuilders")
        hero.p("A declarative way to build HTML, SVG, Markdown, and more.")

    def navigation(self, body):
        nav = body.nav()
        ul = nav.ul(_class="nav")
        ul.li().a("Home", href="#home")
        ul.li().a("Docs", href="#docs")
        ul.li().a("Examples", href="#examples")

    def features(self, body):
        content = body.div(id="content")
        content.h2("Features")
        features = content.ul()
        features.li("112 HTML5 elements with grammar validation")
        features.li("Declarative data binding with ^pointers")
        features.li("Reactive updates via subscribe()")
        features.li("Components for reusable UI patterns")


app = StaticPage()
html = app.render()

output = HERE / "02_static_page.html"
output.write_text(html)
print(html)
print(f"\nSaved to {output}")
