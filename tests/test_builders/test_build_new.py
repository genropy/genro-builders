# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the new build algorithm (rebuild from scratch).

Step (a): the new build() is a no-op. Source is populated, built is empty,
render produces no markup that comes from the source.

Step (b): the no-op holds for sources of different shapes (multiple
children, nested nodes).
"""

from genro_builders.contrib.html import HtmlManager


class HelloDiv(HtmlManager):
    def main(self, source):
        source.body().div()


class TwoChildren(HtmlManager):
    def main(self, source):
        body = source.body()
        body.div()
        body.p("hello")


class NestedNodes(HtmlManager):
    def main(self, source):
        body = source.body()
        outer = body.div(id="outer")
        outer.span("inner")


class DeepNesting(HtmlManager):
    def main(self, source):
        body = source.body()
        section = body.div(id="section")
        article = section.div(id="article")
        article.p("deep")


class TestBuildNewStepA:
    """Step (a): single div in the source, built must remain empty."""

    def test_built_is_empty_after_run(self):
        """After run(), the built bag of the page builder is empty."""
        app = HelloDiv()
        app.run()
        assert len(app.page.built) == 0

    def test_render_does_not_emit_source_markup(self):
        """Render output contains no tag that came from the source."""
        app = HelloDiv()
        result = app.render()
        assert "<div" not in result
        assert "<body" not in result


class TestBuildNewStepB:
    """Step (b): no-op holds for richer source shapes."""

    def test_two_children_built_empty(self):
        app = TwoChildren()
        app.run()
        assert len(app.page.built) == 0

    def test_two_children_render_empty(self):
        app = TwoChildren()
        result = app.render()
        assert "<div" not in result
        assert "<p" not in result
        assert "<body" not in result

    def test_nested_built_empty(self):
        app = NestedNodes()
        app.run()
        assert len(app.page.built) == 0

    def test_nested_render_empty(self):
        app = NestedNodes()
        result = app.render()
        assert "<span" not in result
        assert "<div" not in result
        assert "<body" not in result

    def test_deep_nesting_built_empty(self):
        app = DeepNesting()
        app.run()
        assert len(app.page.built) == 0

    def test_deep_nesting_render_empty(self):
        app = DeepNesting()
        result = app.render()
        assert "<p" not in result
        assert "<div" not in result
        assert "<body" not in result
