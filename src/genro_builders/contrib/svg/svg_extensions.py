# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Genro extensions to the SVG grammar.

This mixin sits on top of ``SvgElements`` in ``SvgBuilder`` MRO.
It declares Genro-specific overrides — currently:

- ``foreignObject`` as a sub-builder entry point that re-enters the
  HTML dialect. The native SVG entry (in ``SvgElements``) treats it
  as a container element; the Extensions override turns it into a
  proper ``@subbuilder("html")`` so HTML content can be authored
  with HTML grammar inside an SVG document.
"""

from __future__ import annotations

from genro_builders.builder import subbuilder


class SvgExtensions:
    """Mixin layering Genro-specific decorators above the SVG grammar."""

    @subbuilder("html")
    def foreignObject(self): ...
