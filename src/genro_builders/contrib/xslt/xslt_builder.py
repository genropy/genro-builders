# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XsltBuilder — XSLT 1.0 dialect for genro-builders.

The grammar is the XSLT instructions from ``XsltElements`` plus the whole
HTML5 vocabulary from ``Html5Elements`` (the literal result elements an
XSLT stylesheet copies to its output). Rendering is the core
``XmlRenderer`` (an XSLT stylesheet is XML): no dialect-specific renderer.
The ``xslt:`` prefixes are composed at render time from the elements'
``_meta`` and the ``xmlns_xslt`` declaration on the stylesheet root.

The HTML elements carry their real (restrictive) ``sub_tags``, but an
XSLT instruction may appear inside any of them; ``XsltBuilder`` overrides
``custom_require_sub_tag_validation`` so an ``xslt:*`` node is never
validated against its parent's sub_tags.
"""

from __future__ import annotations

from typing import Any

from genro_builders.xml import XmlBuilderBase, XmlHandler

from ..html.html5_elements import Html5Elements
from .xslt_elements import XsltElements


class XsltBuilder(XmlBuilderBase, XsltElements, Html5Elements):
    """XSLT 1.0 dialect builder. Grammar only — rendering on the core
    ``XmlRenderer`` via the inherited ``renderer_xml`` property."""

    _name = "xslt"

    def custom_require_sub_tag_validation(self, node: Any) -> bool:
        """An XSLT instruction (``render_tag`` like ``xslt:for-each``) may
        appear inside any element, so it is exempt from the parent's
        sub_tags validation. Literal result elements validate normally."""
        return not (node._get_meta("render_tag") or "").startswith("xslt:")


class XsltBuilderHandler(XmlHandler):
    """Preset handler bound to :class:`XsltBuilder`."""

    builder_class = XsltBuilder


if __name__ == "__main__":
    handler = XsltBuilderHandler()
    handler.create()
    print(handler.render(target=False))
