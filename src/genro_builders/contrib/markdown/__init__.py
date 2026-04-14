# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Markdown builder and renderer module."""

from typing import Any

from genro_builders.manager import ReactiveManager

from .markdown_builder import MarkdownBuilder, MarkdownRenderer


class MarkdownManager(ReactiveManager):
    """Single-builder Markdown manager.

    Subclass and implement ``store()`` / ``main()`` to create a Markdown app.
    The builder is available as ``self.page``.
    """

    def on_init(self):
        self.page = self.register_builder("page", MarkdownBuilder)

    def render(self, **kwargs: Any) -> str:
        """Render the Markdown document. Calls run() automatically if needed."""
        if not len(self.page.built):
            self.run()
        return self.page.render(**kwargs)


__all__ = ["MarkdownBuilder", "MarkdownManager", "MarkdownRenderer"]
