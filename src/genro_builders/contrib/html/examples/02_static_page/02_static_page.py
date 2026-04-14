# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""02 — Static Page: structure, nesting, and composition.

What you learn:
    - Split main() into methods for logical composition
    - Full HTML structure: head + body
    - Nesting: div > h2 + ul > li
    - Attributes: _class (maps to class), id, href
    - Python methods = reusable building blocks

Prerequisites: 01_hello_world

Usage:
    python 02_static_page.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlManager


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
        head.style("""
            .page { font-family: sans-serif; max-width: 600px; margin: 2em auto;
                    color: #333; background: #fff; padding: 1.5em; border-radius: 8px; }
            .hero { background: #eef2ff; padding: 1.5em; border-radius: 8px; margin-bottom: 1em; }
            h1, h2 { color: #1e293b; }
            .nav { list-style: none; padding: 0; display: flex; gap: 1em; }
            .nav li a { text-decoration: none; color: #2563eb; }
            ul { color: #475569; }
            footer { margin-top: 2em; color: #94a3b8; font-size: 0.9em; }
        """)

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

output = Path(__file__).with_suffix(".html")
output.write_text(html)
print(html)
print(f"\nSaved to {output}")
