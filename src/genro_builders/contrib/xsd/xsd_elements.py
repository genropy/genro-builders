# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSD 1.0 grammar (working subset) for genro-builders.

An XSD schema is XML, so it renders through the core ``XmlRenderer`` with
no new renderer. Every element declares ``ns="xs"``: the renderer composes
the prefixed tag ``xs:<method-name>`` (``sequence`` -> ``xs:sequence``), so
the prefix is declared once per element rather than spelled out in a
``render_tag``. The ``xs`` prefix is bound by the user as an ``xmlns_xs``
attribute on the ``schema`` root (emitted as ``xmlns:xs``).

The ``element`` decorator is imported under the alias ``el`` because this
grammar declares a method literally named ``element`` (the ``xs:element``
tag): after ``def element`` the bare name ``element`` would resolve, for
the following methods, to the just-defined marker instead of the
decorator. Aliasing the decorator keeps every method named exactly after
its XSD tag. (A reusable escape for any grammar whose tag names collide
with a decorator name.)

``import`` is a Python keyword, so its method is ``import_``; the renderer
strips the trailing underscore before composing (``import_`` -> ``import``
-> ``xs:import``). No docstrings on the elements: XSD is a standard
vocabulary (like HTML5/SVG), the tag names are the documentation.

Covered subset (the tags a real-world schema such as FatturaPA uses):
structure (schema, element, complexType, simpleType, sequence, choice,
all, attribute), simple-type facets (restriction, enumeration, pattern,
length, minLength, maxLength, minInclusive, maxInclusive, whiteSpace),
annotations (annotation, documentation, appinfo), composition (import,
include). ``appinfo`` is a catch-all: it hosts arbitrary application
vocabularies (an ``<editor>`` in its own namespace).
"""

from __future__ import annotations

from genro_builders.builder import element as el


class XsdElements:
    """Mixin: the XSD vocabulary (``xs:*``), composed via ``ns="xs"``."""

    # -- structure --------------------------------------------------------
    @el(sub_tags="*", ns="xs")
    def schema(self, **kwargs): ...

    @el(sub_tags="*", ns="xs")
    def element(self, **kwargs): ...

    @el(sub_tags="*", ns="xs")
    def complexType(self, **kwargs): ...

    @el(sub_tags="*", ns="xs")
    def simpleType(self, **kwargs): ...

    @el(sub_tags="*", ns="xs")
    def sequence(self, **kwargs): ...

    @el(sub_tags="*", ns="xs")
    def choice(self, **kwargs): ...

    @el(sub_tags="*", ns="xs")
    def all(self, **kwargs): ...

    @el(sub_tags="*", ns="xs")
    def attribute(self, **kwargs): ...

    # -- simple-type facets ----------------------------------------------
    @el(sub_tags="*", ns="xs")
    def restriction(self, **kwargs): ...

    @el(sub_tags="*", ns="xs")
    def enumeration(self, **kwargs): ...

    @el(sub_tags="", ns="xs")
    def pattern(self, **kwargs): ...

    @el(sub_tags="", ns="xs")
    def length(self, **kwargs): ...

    @el(sub_tags="", ns="xs")
    def minLength(self, **kwargs): ...

    @el(sub_tags="", ns="xs")
    def maxLength(self, **kwargs): ...

    @el(sub_tags="", ns="xs")
    def minInclusive(self, **kwargs): ...

    @el(sub_tags="", ns="xs")
    def maxInclusive(self, **kwargs): ...

    @el(sub_tags="", ns="xs")
    def whiteSpace(self, **kwargs): ...

    # -- annotations ------------------------------------------------------
    @el(sub_tags="*", ns="xs")
    def annotation(self, **kwargs): ...

    @el(sub_tags="*", ns="xs")
    def documentation(self, **kwargs): ...

    @el(sub_tags="*", ns="xs")
    def appinfo(self, **kwargs): ...

    # -- composition ------------------------------------------------------
    @el(sub_tags="", ns="xs")
    def import_(self, **kwargs): ...

    @el(sub_tags="", ns="xs")
    def include(self, **kwargs): ...
