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

from genro_builders.builder import subbuilder


class Html5Extensions:
    """Mixin layering Genro-specific decorators above the W3C grammar."""

    @subbuilder("svg")
    def svg(self):
        """Switch to the SVG dialect from this node down (BLD.2)."""
