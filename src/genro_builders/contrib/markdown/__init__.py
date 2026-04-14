# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Markdown builder and renderer module."""

from genro_builders.manager import ReactiveManager

from .markdown_builder import MarkdownBuilder, MarkdownRenderer


class MarkdownManager(ReactiveManager):
    """Single-builder Markdown manager.

    Subclass and implement ``store()`` / ``main()`` to create a Markdown app.
    The builder is available as ``self.page``.
    """

    def __init__(self):
        self.page = self.set_builder("page", MarkdownBuilder)


__all__ = ["MarkdownBuilder", "MarkdownManager", "MarkdownRenderer"]
