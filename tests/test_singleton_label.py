# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the singleton label: an element the parent declares AT MOST
ONCE is labelled with its tag, not with an ordinal.

``x[1]`` and ``x[0:1]`` are both singletons — only the maximum matters,
since what makes the ordinal pointless is that a second one cannot exist.
Strict, like a collection key: an explicit ``node_label=`` raises, and so
does a second node claiming the label, which would otherwise silently
overwrite the first.

Exercised through a minimal inline builder, no dialect dependency.
"""
from __future__ import annotations

import pytest

from genro_builders.builder import BuilderBase, element
from genro_builders.contrib.html import HtmlBuilder


class _DocBuilder(BuilderBase):
    _name = "_singletontest"
    _default_render_mode = "xml"

    # head: exactly one. note: 0..N. caption: optional, still at most one.
    @element(sub_tags="head[1],note,caption[0:1]")
    def doc(self, **kwargs): ...

    @element(parent_tags="doc")
    def head(self, **kwargs): ...

    @element(parent_tags="doc")
    def note(self, **kwargs): ...

    @element(parent_tags="doc")
    def caption(self, **kwargs): ...


def _build(main):
    class _D(_DocBuilder):
        pass

    _D.main = lambda self, root: main(root)
    page = _D()
    page.create()
    return page


def _children(page):
    """The labels of the (single) container's children."""
    container = next(iter(page.source))
    return [n.label for n in container.value]


def test_mandatory_singleton_labelled_by_tag():
    """``head[1]`` -> the label is ``head``, with no ordinal."""
    page = _build(lambda root: root.doc().head())
    assert _children(page) == ["head"]


def test_optional_singleton_labelled_by_tag():
    """``caption[0:1]`` is a singleton too: only the MAXIMUM matters."""
    page = _build(lambda root: root.doc().caption("title"))
    assert _children(page) == ["caption"]


def test_singleton_reachable_by_tag():
    """The point of the stable label: reach the node by its tag."""
    page = _build(lambda root: root.doc().head(lang="it"))
    container = next(iter(page.source))
    assert container.value.get_node("head").attr.get("lang") == "it"


def test_unbounded_sibling_still_auto_labels():
    """A tag declared without cardinality keeps its ordinals."""
    page = _build(
        lambda root: (lambda d: (d.note(), d.note()))(root.doc()),
    )
    assert _children(page) == ["note_0", "note_1"]


def test_second_singleton_raises_instead_of_overwriting():
    """A second one cannot exist: it raises rather than replacing the first.

    Without this the second insertion would reuse the label and drop the
    first node's content without a word.
    """
    with pytest.raises(ValueError, match="declared at most once"):
        _build(lambda root: (lambda d: (d.head(), d.head()))(root.doc()))


def test_explicit_node_label_on_singleton_raises():
    """The label belongs to the grammar, so forcing one is an error."""
    with pytest.raises(ValueError, match="node_label is not allowed"):
        _build(lambda root: root.doc().head(node_label="forced"))


def test_render_ignores_the_label():
    """The label names the node; the emitted tag comes from ``node_tag``."""
    page = _build(lambda root: root.doc().head("x"))
    assert page.render(target=False) == "<doc><head>x</head></doc>"


# --------------------------------------------------------------------------
# The HTML5 grammar declares the at-most-one children the spec defines, so
# the labels below are derived, not spelled out with ``node_label``.
# --------------------------------------------------------------------------


def _html_page(main):
    class _P(HtmlBuilder):
        pass

    _P.main = lambda self, root: main(root)
    page = _P()
    page.create()
    return page


def test_html_singletons_reachable_by_tag():
    """``head``/``body``/``title`` carry stable labels, not ordinals."""
    page = _html_page(
        lambda root: (lambda h: (h.head().title("T"), h.body()))(root.html()),
    )
    html = next(iter(page.source)).value
    assert [n.label for n in html] == ["head", "body"]
    assert html.get_node("head").value.get_node("title").value == "T"


def test_table_mixes_singletons_and_repeatables():
    """``caption``/``thead`` are at most one; ``tbody`` is unbounded."""
    page = _html_page(
        lambda root: (
            lambda t: (t.caption("c"), t.thead(), t.tbody(), t.tbody())
        )(root.body().table()),
    )
    table = next(iter(page.source)).value.get_node("table_0").value
    assert [n.label for n in table] == ["caption", "thead", "tbody_0", "tbody_1"]


def test_second_body_raises_instead_of_silently_replacing():
    """Before the cardinality was declared this dropped the first body."""
    with pytest.raises(ValueError, match="declared at most once"):
        _html_page(lambda root: (lambda h: (h.body(), h.body()))(root.html()))
