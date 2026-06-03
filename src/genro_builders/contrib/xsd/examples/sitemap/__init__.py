# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XML Sitemap example: a small generated XSD dialect.

Reference example of the codegen pipeline on a tiny, widely-known schema.
``sitemap.py`` is generated from ``sitemap.xsd`` and declares
``SitemapBuilder`` (grammar) + ``SitemapHandler`` (preset).
"""

from __future__ import annotations

from genro_builders.contrib.xsd.examples.sitemap.sitemap import (
    SitemapBuilder,
    SitemapHandler,
)

__all__ = ["SitemapBuilder", "SitemapHandler"]
