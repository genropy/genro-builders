# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XML core — shared grammar base for XML-on-the-wire dialects.

:class:`XmlBuilderBase` (grammar, ``xml`` default mode) anchors the
dialects whose serialized form is XML — XSLT and the schema-generated
dialects today. It carries no namespace state of its own: the
namespace-tag mechanism (``_meta`` ``ns``/``local`` → ``<prefix:local>``,
``xmlns_<prefix>`` attributes) lives on the core ``XmlRenderer``. A
dialect builder creates and renders itself like any other
(``doc = MyBuilder(); doc.create(); doc.render()``).
"""

from __future__ import annotations

from .xml_builder import XmlBuilderBase

__all__ = [
    "XmlBuilderBase",
]
