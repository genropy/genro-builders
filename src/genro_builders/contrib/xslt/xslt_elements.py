# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSLT 1.0 grammar (working subset) for genro-builders.

An XSLT stylesheet is XML, so it renders through the core ``XmlRenderer``
with no new renderer. Two element families share one tree:

- **XSLT instructions** (``xsl:template``, ``xsl:for-each``, ...). Each
  declares ``_meta={"render_tag": "xsl:<local>"}``: the Python method
  name stays a legal identifier (``for_each``) while the emitted tag is
  the prefixed name (``xsl:for-each``). This reuses the renderer's
  existing ``render_tag`` mechanism (the same one that turns the SVG
  ``html`` sub-builder into ``<foreignObject>``) — no XSLT-specific
  render code. The ``xsl`` prefix is declared once by the user as an
  ``xmlns_xsl`` attribute on the ``stylesheet`` root (emitted as
  ``xmlns:xsl``).

- **Literal result elements** (``html``, ``table``, ``tr``, ...). Plain
  ``@element`` with no ``render_tag``: copied to the output verbatim. In
  XSLT these are *part of the stylesheet grammar*, interleaved with the
  instructions at the same level — which is why they live here rather
  than in a nested HTML sub-builder (a sub-builder switches the active
  grammar irreversibly, so an ``xsl:for-each`` inside an HTML ``<table>``
  would be unreachable).

Attribute names like ``select``/``match``/``test`` are XPath and are
emitted verbatim. ``{...}`` attribute-value-templates pass through too
(only ``${...}`` is a builder template, only ``^``/``=`` a pointer).
"""

from __future__ import annotations

from genro_builders.builder import element


class XsltElements:
    """Mixin: the XSLT instruction vocabulary + literal result elements."""

    # -------------------------------------------------------------------
    # XSLT instructions (xsl:* namespace)
    # -------------------------------------------------------------------

    @element(sub_tags="*", _meta={"render_tag": "xsl:stylesheet"})
    def stylesheet(self):
        """Root of a stylesheet. Carries ``version`` and the namespace
        declaration ``xmlns_xsl`` (emitted as ``xmlns:xsl``)."""
        ...

    @element(_meta={"render_tag": "xsl:output"})
    def output(self):
        """Serialization options for the result tree (``method``,
        ``encoding``, ``indent``)."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:template"})
    def template(self):
        """A transformation rule, selected by ``match`` (pattern) or
        invoked by ``name``."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:apply-templates"})
    def apply_templates(self):
        """Process the nodes chosen by ``select`` with their matching
        templates."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:call-template"})
    def call_template(self):
        """Invoke a named template (``name``)."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:param"})
    def param(self):
        """A template/stylesheet parameter (``name``, optional default
        via ``select`` or body)."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:with-param"})
    def with_param(self):
        """Pass an argument (``name``, ``select``) to a called template."""
        ...

    @element(_meta={"render_tag": "xsl:value-of"})
    def value_of(self):
        """Insert the string value of the XPath ``select`` into the
        output."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:for-each"})
    def for_each(self):
        """Iterate over the node-set chosen by ``select``."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:if"})
    def if_(self):
        """Conditional: emit the body when the XPath ``test`` is true.
        Named ``if_`` (``if`` is a Python keyword); the emitted tag is
        ``xsl:if`` from ``render_tag``, independent of the method name."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:choose"})
    def choose(self):
        """Multi-branch conditional: a series of ``when`` plus an
        optional ``otherwise``."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:when"})
    def when(self):
        """A branch of ``choose``, taken when its ``test`` is true."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:otherwise"})
    def otherwise(self):
        """The fallback branch of ``choose``."""
        ...

    @element(_meta={"render_tag": "xsl:text"})
    def text(self):
        """Literal text, with control over output escaping/whitespace."""
        ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:variable"})
    def variable(self):
        """A named variable (``name``, value via ``select`` or body)."""
        ...

    # -------------------------------------------------------------------
    # Literal result elements (no namespace; copied to the output)
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def html(self): ...

    @element(sub_tags="*")
    def head(self): ...

    @element(sub_tags="*")
    def title(self): ...

    @element(sub_tags="*")
    def body(self): ...

    @element(sub_tags="*")
    def h1(self): ...

    @element(sub_tags="*")
    def h2(self): ...

    @element(sub_tags="*")
    def p(self): ...

    @element(sub_tags="*")
    def table(self): ...

    @element(sub_tags="*")
    def thead(self): ...

    @element(sub_tags="*")
    def tbody(self): ...

    @element(sub_tags="*")
    def tr(self): ...

    @element(sub_tags="*")
    def th(self): ...

    @element(sub_tags="*")
    def td(self): ...

    @element(sub_tags="*")
    def a(self): ...

    @element(sub_tags="*")
    def div(self): ...

    @element(sub_tags="*")
    def span(self): ...
