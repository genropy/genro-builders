# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XML core — shared base for XML-on-the-wire dialects.

:class:`XmlBuilderBase` (grammar, ``xml`` default mode) and
:class:`XmlHandler` (engine preset) anchor the dialects whose serialized
form is XML — XSLT and the schema-generated dialects today. They carry no namespace state of their
own: the namespace-tag mechanism (``_meta`` ``ns``/``local`` →
``<prefix:local>``, ``xmlns_<prefix>`` attributes) lives on the core
``XmlRenderer``.
"""

from __future__ import annotations

from .xml_builder import XmlBuilderBase, XmlHandler

__all__ = [
    "XmlBuilderBase",
    "XmlHandler",
]
