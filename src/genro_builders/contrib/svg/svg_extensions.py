# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Genro extensions to the SVG grammar.

This mixin sits on top of ``SvgElements`` in ``SvgBuilder`` MRO.
It declares Genro-specific additions:

- ``html`` as a user-facing entry point that re-enters the HTML
  dialect. At render time the framework wraps the HTML subtree in
  ``<foreignObject xmlns="http://www.w3.org/1999/xhtml">`` so the
  output satisfies the SVG embedding rule, while the source bag
  keeps the natural name ``html``.

The W3C ``foreignObject`` element is left as a plain ``@element``
on ``SvgElements`` for users who want to author the envelope by
hand; in practice the ``html`` subbuilder is the recommended path.
"""

from __future__ import annotations

from genro_builders.builder import subbuilder


class SvgExtensions:
    """Mixin layering Genro-specific decorators above the SVG grammar."""

    @subbuilder("html")
    def html(self):
        """Switch to the HTML dialect from this node down (BLD.2).

        Rendered inside an SVG ``<foreignObject>`` envelope via
        :meth:`wrapper_html`.
        """

    def wrapper_html(self) -> dict:
        """Boundary markup emitted around an embedded HTML subtree.

        The XHTML namespace on the foreignObject envelope is required
        for the document to be XML well-formed at the SVG/HTML
        boundary.
        """
        return {
            "tag": "foreignObject",
            "attrs": {"xmlns": "http://www.w3.org/1999/xhtml"},
        }
