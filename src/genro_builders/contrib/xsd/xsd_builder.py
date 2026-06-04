# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XsdBuilderBase + XsdHandler — base classes for XSD-born dialects.

A dialect generated from an XSD schema is a builder whose grammar is the
schema's element vocabulary and whose on-the-wire format is XML. The
codegen pipeline (``contrib/xsd/codegen``) writes a Python module with a
concrete ``<Schema>Builder(XsdBuilderBase)`` + ``<Schema>Handler(XsdHandler)``
pair; the user subclasses the handler and implements ``main``.

These two bases are intentionally light. The real XML render lives in the
core (``XmlRenderer`` on ``RendererBase``, exposed by
``BagBuilderBase.renderer_xml``): every dialect already serves ``xml`` with
pointers resolved and framework markers filtered. What ``XsdBuilderBase``
adds is the semantic anchor for XSD-born dialects — a single place to fix
``xml`` as the default render mode, and the future home for the XSD
constraints the grammar does not yet emit (``totalDigits``, ``minLength``,
surfaced today as ``# NOTE: ... grammar gap`` comments in generated code).
"""

from __future__ import annotations

from ..xml.xml_builder import XmlBuilderBase, XmlHandler


class XsdBuilderBase(XmlBuilderBase):
    """Grammar base for dialects generated from an XSD schema.

    An XSD-born dialect is XML on the wire, so it sits on
    :class:`XmlBuilderBase` (which fixes ``xml`` as the default render
    mode). Concrete grammars (``FatturaElettronicaBuilder``,
    ``GpxBuilder``, ...) subclass this and add their ``@element``
    vocabulary.
    """


class XsdHandler(XmlHandler):
    """Handler base for XSD-born dialects.

    A concrete ``<Schema>Handler`` subclass binds its ``builder_class`` to
    the matching ``<Schema>Builder``. Nothing else is needed here: the
    engine, the lifecycle, and the XML render all come from the core.
    """


if __name__ == "__main__":
    builder = XsdBuilderBase
    print(f"{builder.__name__} default mode: {builder._default_render_mode}")
