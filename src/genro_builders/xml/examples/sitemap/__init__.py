# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XML Sitemap example: a small dialect generated from an XSD schema.

Reference example of the XML transpiler on a tiny, widely-known schema.
``sitemap.py`` is generated from ``sitemap.xsd`` and declares
``SitemapBuilder`` (grammar). It creates and renders itself like any
other dialect.
"""

from __future__ import annotations

from .sitemap import SitemapBuilder

__all__ = ["SitemapBuilder"]
