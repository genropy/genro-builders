# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XML Sitemap example: a small dialect generated from an XSD schema.

Reference example of the XML transpiler on a tiny, widely-known schema.
``sitemap.py`` is generated from ``sitemap.xsd`` and declares
``SitemapBuilder`` (grammar) + ``SitemapHandler`` (preset).
"""

from __future__ import annotations

from .sitemap import (
    SitemapBuilder,
    SitemapHandler,
)

__all__ = ["SitemapBuilder", "SitemapHandler"]
