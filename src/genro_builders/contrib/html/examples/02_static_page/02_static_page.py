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
        self.hero(body)
        self.navigation(body)
        self.features(body)
        body.footer().p("Built with genro-builders.")

    def page_head(self, source):
        head = source.head()
        head.meta(charset="utf-8")
        head.title("My Static Page")
        head.style("""
            body { font-family: sans-serif; max-width: 600px; margin: 2em auto; }
            .hero { background: #f0f4f8; padding: 1.5em; border-radius: 8px; }
            .nav { list-style: none; padding: 0; display: flex; gap: 1em; }
            .nav li a { text-decoration: none; color: #2563eb; }
            footer { margin-top: 2em; color: #666; font-size: 0.9em; }
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
