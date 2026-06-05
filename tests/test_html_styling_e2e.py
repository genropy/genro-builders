# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""End-to-end tests for HtmlRenderer styling: CSS roots, Genro macros,
three-state values and the reactive ``include_datapath`` mode.

All tests drive a real ``HtmlBuilderHandler`` and assert on the rendered
markup — outcomes, never internals. They include negative assertions
(what must NOT be in the output), the class of check that would have
caught the ``datapath`` leak.
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilderHandler


def _render(build, **opts):
    """Render a page whose ``main`` runs ``build(root)``."""

    class _P(HtmlBuilderHandler):
        def main(self, root):
            build(root)

    page = _P()
    page.create()
    return page.render(target=False, **opts)


# ---------------------------------------------------------------------------
# CSS roots and explicit style
# ---------------------------------------------------------------------------

def test_css_root_attrs_become_style():
    out = _render(lambda root: root.body().div(color="red", width=100))
    assert 'style="color: red; width: 100"' in out
    # negative: CSS roots must NOT surface as plain attributes
    assert 'color="red"' not in out
    assert 'width="100"' not in out


def test_explicit_style_string_merged():
    out = _render(lambda root: root.body().div(style="margin: 0", color="blue"))
    assert "margin: 0" in out
    assert "color: blue" in out


def test_style_underscore_escape_is_literal_css():
    out = _render(lambda root: root.body().div(style_aspect_ratio="16/9"))
    assert 'style="aspect-ratio: 16/9"' in out


def test_html_prefix_escape_forces_attribute():
    # ``html_width`` is the explicit escape: emit the HTML attribute, not CSS.
    out = _render(lambda root: root.body().div(html_width=100))
    assert 'width="100"' in out
    assert "style=" not in out


# ---------------------------------------------------------------------------
# Genro CSS macros
# ---------------------------------------------------------------------------

def test_macro_rounded_four_corners():
    out = _render(lambda root: root.body().div(rounded=8))
    for corner in ("top-left", "top-right", "bottom-left", "bottom-right"):
        assert f"border-{corner}-radius: 8px" in out


def test_macro_rounded_per_side_subkwarg():
    out = _render(lambda root: root.body().div(rounded_top=4))
    assert "border-top-left-radius: 4px" in out
    assert "border-top-right-radius: 4px" in out
    assert "border-bottom-left-radius" not in out


def test_macro_transform_typed_functions():
    out = _render(
        lambda root: root.body().div(
            transform_rotate=45, transform_scale=2, transform_translate_x=10,
        ),
    )
    assert "rotate(45deg)" in out
    assert "scale(2)" in out
    assert "translateX(10px)" in out


def test_macro_rounded_per_side_bottom_left():
    out = _render(lambda root: root.body().div(rounded_bottom=5, rounded_left=3))
    assert "border-bottom-left-radius: 3px" in out
    assert "border-bottom-right-radius: 5px" in out
    assert "border-top-left-radius: 3px" in out


def test_macro_filter_functions():
    out = _render(
        lambda root: root.body().div(filter_blur=3, filter_invert=1),
    )
    assert "blur(3px)" in out
    assert "invert(1)" in out


def test_macro_transform_skew_and_filter_drop_shadow():
    out = _render(
        lambda root: root.body().div(
            transform_skew_x=10, filter_drop_shadow="2px 2px red",
        ),
    )
    assert "skewX(10deg)" in out
    assert "drop-shadow(2px 2px red)" in out


def test_underscore_keyword_attr_remap():
    # ``_class`` collides with no python keyword issue but remaps to ``class``.
    out = _render(lambda root: root.body().div(_class="lbl"))
    assert 'class="lbl"' in out
    assert "_class" not in out


def test_macro_shadow_and_gradient_passthrough():
    out = _render(
        lambda root: root.body().div(
            shadow="0 2px 4px #000",
            gradient="linear-gradient(red, blue)",
        ),
    )
    assert "box-shadow: 0 2px 4px #000" in out
    assert "background-image: linear-gradient(red, blue)" in out


def test_macro_transition_and_zoom():
    out = _render(lambda root: root.body().div(transition="all 0.2s", zoom=1.5))
    assert "transition: all 0.2s" in out
    assert "zoom: 1.5" in out


# ---------------------------------------------------------------------------
# Three-state attribute values
# ---------------------------------------------------------------------------

def test_boolean_attribute_values():
    out = _render(lambda root: root.body().input(disabled=True, readonly=False))
    assert 'disabled="true"' in out
    assert 'readonly="false"' in out


def test_none_attribute_value_is_dropped():
    # A None attribute is treated as absent — no attribute is emitted.
    out = _render(lambda root: root.body().input(value=None))
    assert "<input/>" in out
    assert "value=" not in out


# ---------------------------------------------------------------------------
# Void tags
# ---------------------------------------------------------------------------

def test_void_tag_self_closes_xml_style():
    out = _render(lambda root: root.body().br())
    assert "<br/>" in out


def test_void_tag_html_style():
    out = _render(lambda root: root.body().br(), xml=False)
    assert "<br>" in out
    assert "<br/>" not in out


# ---------------------------------------------------------------------------
# Reactive render: include_datapath
# ---------------------------------------------------------------------------

class _BoundPage(HtmlBuilderHandler):
    def setup(self):
        self.data.set_item("f.v", "X")

    def main(self, root):
        root.body(datapath="f").input(value="^.v")


def test_include_datapath_emits_id_and_pointer():
    page = _BoundPage()
    page.create()
    out = page.render(target=False, include_datapath=True)
    assert 'value="X"' in out
    assert 'data-value-pointer="f.v"' in out
    assert "id=" in out


def test_no_datapath_attribute_leaks_in_markup():
    """The datapath binding root must never surface as an attribute
    (regression guard for the leak fixed in a9dec22)."""
    page = _BoundPage()
    page.create()
    out = page.render(target=False)
    assert "datapath=" not in out
    assert 'value="X"' in out
