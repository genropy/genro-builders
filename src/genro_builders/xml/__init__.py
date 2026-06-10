# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XML core — shared grammar base for XML-on-the-wire dialects.

:class:`XmlBuilderBase` (grammar, ``xml`` default mode) anchors the
dialects whose serialized form is XML — XSLT and the schema-generated
dialects today. It carries no namespace state of its own: the
namespace-tag mechanism (``_meta`` ``ns``/``local`` → ``<prefix:local>``,
``xmlns_<prefix>`` attributes) lives on the core ``XmlRenderer``. A
dialect builder is mounted on the generic ``BuilderHandler`` like any
other (``handler.add_builder(MyBuilder())``).
"""

from __future__ import annotations

from .xml_builder import XmlBuilderBase

__all__ = [
    "XmlBuilderBase",
]
