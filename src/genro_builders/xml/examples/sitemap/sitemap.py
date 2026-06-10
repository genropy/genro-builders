# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
# GENERATED FILE - DO NOT EDIT MANUALLY.
# Regenerate with: python -m genro_builders.xml.transpiler --xsd <path> --dialect-name Sitemap --output <path>
# Source targetNamespace: http://www.sitemaps.org/schemas/sitemap/0.9
"""XML Sitemap dialect, generated from sitemap.xsd (modelled on the public Sitemaps protocol 0.9). A small real-world XSD example: nested urlset/url, enumerated changefreq, bounded priority."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from genro_builders.builder import Range, element
from genro_builders.xml import XmlBuilderBase


class SitemapBuilder(XmlBuilderBase):
    """XSD dialect grammar generated from namespace ``http://www.sitemaps.org/schemas/sitemap/0.9``.
    """

    _name = "sitemap"

    @element(
        sub_tags='url[1:]',
    )
    def urlset(self):
        """The root element; encloses the URL entries of the
      sitemap. Contains one or more url children."""
        ...

    @element(
        sub_tags='loc[1],lastmod[0:1],changefreq[0:1],priority[0:1]',
    )
    def url(self):
        ...

    @element()
    def loc(self, node_value: str | None = None):
        """URL of the page. Required. Args: node_value."""
        ...

    @element()
    def lastmod(self, node_value: str | None = None):
        """Date of last modification (W3C Datetime). Args: node_value."""
        ...

    @element()
    def changefreq(self, node_value: Literal['always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never'] | None = None):
        """How frequently the page is likely to change. Args: node_value."""
        ...

    @element()
    def priority(self, node_value: Annotated[Decimal, Range(ge=0.0, le=1.0)] | None = None):
        """Priority of this URL relative to other URLs
          on the site, from 0.0 to 1.0. Args: node_value."""
        ...

