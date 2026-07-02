# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Unit tests for the ``ns`` decorator parameter (namespace prefix).

``@element(ns='xs')`` declares a namespace prefix once per element; the
shared ``XmlRenderer`` composes ``<ns>:<method-name>`` at render time,
so the prefix is not repeated in every ``render_tag``. Being per-element,
``ns`` supports mixed namespaces in one grammar (prefixed elements next
to bare literal ones). An explicit ``render_tag`` wins over ``ns``.

These tests exercise the renderer in isolation through minimal inline
builders, independent of any dialect. Output type is XML.
"""
from __future__ import annotations

from genro_builders.builder import BuilderBase, BuilderHandler, abstract
from genro_builders.builder import element as el

# ``element`` is imported under an alias because this grammar declares a
# method literally named ``element`` (the XSD ``xs:element`` tag): a bare
# ``@element`` would, after ``def element``, resolve to the just-defined
# marker (not the decorator) for the following methods.


class _NsParamBuilder(BuilderBase):
    """Minimal builder: prefixed elements via ``ns='xs'``, one bare
    element, one keyword-named element, one with an explicit render_tag."""

    _name = "_nsparamtest"
    _default_render_mode = "xml"

    @el(sub_tags="*", ns="xs")
    def schema(self): ...

    @el(sub_tags="*", ns="xs")
    def sequence(self): ...

    @el(ns="xs")
    def element(self): ...

    @el(ns="xs")
    def import_(self): ...  # 'import' is a Python keyword

    @el(sub_tags="*")
    def table(self): ...  # no ns -> bare tag

    @el(ns="xs", _meta={"render_tag": "xs:explicit-wins"})
    def override(self): ...  # explicit render_tag must win over ns


def _render(main, builder=_NsParamBuilder):
    class _H(builder):
        pass

    _H.main = lambda self, root: main(root)
    page = _H()
    BuilderHandler().add_builder(page)
    return page.render(target=False)


def test_ns_composes_prefixed_tag():
    """``ns='xs'`` on method ``sequence`` emits ``<xs:sequence>``."""
    out = _render(lambda root: root.schema().sequence())
    assert "<xs:schema>" in out
    assert "<xs:sequence></xs:sequence>" in out


def test_ns_carries_attributes_verbatim():
    """Attributes pass through unchanged on a prefixed element."""
    out = _render(lambda root: root.schema().element(name="Consultorio", type="xs:string"))
    assert '<xs:element name="Consultorio" type="xs:string">' in out


def test_no_ns_stays_bare():
    """An element without ``ns`` keeps the bare tag."""
    out = _render(lambda root: root.table())
    assert "<table>" in out
    assert "xs:table" not in out


def test_ns_with_keyword_method_strips_then_prefixes():
    """``import_`` (keyword form) -> strip underscore -> prefix: ``xs:import``."""
    out = _render(lambda root: root.import_(namespace="urn:x"))
    assert "<xs:import" in out
    assert "import_" not in out
    assert "xs:import_" not in out


def test_explicit_render_tag_wins_over_ns():
    """An explicit ``render_tag`` beats ``ns`` (the literal tag wins)."""
    out = _render(lambda root: root.override())
    assert "<xs:explicit-wins></xs:explicit-wins>" in out
    assert "xs:override" not in out


def test_mixed_namespaces_in_one_tree():
    """Prefixed and bare elements coexist: the prefix is per-element."""
    out = _render(lambda root: root.schema().sequence().table())
    assert "<xs:schema>" in out
    assert "<xs:sequence>" in out
    assert "<table>" in out  # bare, inside the prefixed ancestors


def test_node_tag_stays_python_legal():
    """The node tag is the Python name; only the emitted markup is prefixed."""

    class _H(_NsParamBuilder):
        def main(self, root):
            root.schema().sequence()

    page = _H()
    BuilderHandler().add_builder(page)
    schema = next(iter(page.source))
    seq = next(iter(schema.value))
    assert seq.node_tag == "sequence"
    assert "<xs:sequence" in page.render(target=False)


class _NsInheritBuilder(BuilderBase):
    """``ns`` declared on an abstract, inherited by concrete elements."""

    _name = "_nsinherittest"
    _default_render_mode = "xml"

    @abstract(sub_tags="*", ns="xs")
    def _xs(self): ...

    @el(sub_tags="*", inherits_from="_xs")
    def schema(self): ...

    @el(inherits_from="_xs")
    def element(self): ...


def test_ns_inherited_from_abstract():
    """An element inheriting from an abstract that carries ``ns`` emits
    the prefixed tag without declaring ``ns`` itself."""
    out = _render(lambda root: root.schema().element(name="X"),
                  builder=_NsInheritBuilder)
    assert "<xs:schema>" in out
    assert '<xs:element name="X">' in out


class _PrefixProbeBuilder(BuilderBase):
    """A method named for the dialect prefix (``prb_element``) avoids
    shadowing the ``element`` decorator; with ``ns='xs'`` the emitted tag
    drops the ``<dialect>_`` prefix and gains the namespace: ``xs:element``.
    Uses a probe ``_name`` (not a real dialect name) so the global builder
    registry is not clobbered when other tests define that dialect."""

    _name = "prb"
    _default_render_mode = "xml"

    @el(sub_tags="*", ns="xs")
    def schema(self): ...

    @el(sub_tags="*", ns="xs")
    def prb_element(self): ...


def test_dialect_prefix_stripped_before_ns_compose():
    """``prb_element`` + ``ns='xs'`` -> ``xs:element`` (``<dialect>_`` dropped)."""
    out = _render(lambda root: root.schema().prb_element(name="Consultorio"),
                  builder=_PrefixProbeBuilder)
    assert '<xs:element name="Consultorio">' in out
    assert "prb_element" not in out
    assert "xs:prb_element" not in out
