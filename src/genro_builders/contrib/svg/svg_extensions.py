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

from genro_builders.builder import element


class SvgExtensions:
    """Mixin layering Genro-specific decorators above the SVG grammar."""

    @element(
        _meta={
            "subbuilder": "html",
            "render_tag": "foreignObject",
            "render_attributes": {"xmlns": "http://www.w3.org/1999/xhtml"},
        },
    )
    def html(self):
        """Switch to the HTML dialect from this node down (BLD.2).

        A sub-builder element: ``_meta['subbuilder']`` switches the active
        dialect to HTML from this node down. The source tag ``html`` is
        rendered as ``_meta['render_tag']`` (``<foreignObject>``) carrying
        ``_meta['render_attributes']`` (the XHTML namespace), required for
        the document to be XML well-formed at the SVG/HTML boundary.
        """
