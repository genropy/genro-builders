# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Genro extensions to the HTML5 grammar.

This mixin sits on top of ``Html5Elements`` in ``HtmlBuilder`` MRO.
It declares all Genro-specific additions that are NOT in the W3C
auto-generated schema:

- ``svg`` as a sub-builder entry point that switches the active
  grammar to the SVG dialect.

The W3C-generated mixin (``Html5Elements``) is regenerated from the
RELAX NG schema; keeping Genro additions here insulates them from
regeneration.
"""

from __future__ import annotations

from genro_builders.builder import element


class Html5Extensions:
    """Mixin layering Genro-specific decorators above the W3C grammar."""

    @element(_meta={"subbuilder": "svg"})
    def svg(self, **kwargs):
        """Switch to the SVG dialect from this node down (BLD.2).

        A sub-builder element: ``_meta['subbuilder']`` switches the active
        dialect to SVG from this node down. No ``render_tag``: ``<svg>`` is
        emitted verbatim (HTML5 has a native ``<svg>`` tag)."""
