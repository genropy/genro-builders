# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HTML5 content-model contract for elements corrected in Html5Extensions."""

import pytest

from genro_builders.contrib.html import HtmlBuilder


class DetailsPage(HtmlBuilder):
    def main(self, root):
        panel = root.details()
        panel.summary("JavaScript source · XML")
        panel.pre("Source preview")
        panel.p("A paragraph")
        panel.div("A div")


class TwoSummaries(HtmlBuilder):
    def main(self, root):
        panel = root.details()
        panel.summary("first")
        panel.summary("second")


def test_details_accepts_summary_then_flow_content():
    page = DetailsPage()
    page.create()
    assert page.render(target=False) == (
        "<details><summary>JavaScript source · XML</summary>"
        "<pre>Source preview</pre><p>A paragraph</p><div>A div</div></details>"
    )


def test_details_rejects_a_second_summary():
    with pytest.raises(
        ValueError,
        match="'summary' is declared at most once in 'details' and is already present",
    ):
        TwoSummaries().create()


def test_details_rejects_non_flow_content():
    class BadPage(HtmlBuilder):
        def main(self, root):
            root.details().td()

    with pytest.raises(ValueError, match="'td' not allowed as child of 'details'"):
        BadPage().create()


class FieldsetPage(HtmlBuilder):
    def main(self, root):
        box = root.fieldset()
        box.legend("Options")
        box.input(type="text")
        box.p("A paragraph")


def test_fieldset_accepts_legend_then_flow_content():
    page = FieldsetPage()
    page.create()
    assert page.render(target=False) == (
        "<fieldset><legend>Options</legend><input type=\"text\"/>"
        "<p>A paragraph</p></fieldset>"
    )


def test_dl_accepts_dt_and_dd():
    class Page(HtmlBuilder):
        def main(self, root):
            dl = root.dl()
            dl.dt("Term")
            dl.dd("Definition")

    page = Page()
    page.create()
    assert page.render(target=False) == (
        "<dl><dt>Term</dt><dd>Definition</dd></dl>"
    )


def test_time_accepts_phrasing_content():
    class Page(HtmlBuilder):
        def main(self, root):
            root.time(datetime="2026-09-06").b("today")

    page = Page()
    page.create()
    assert page.render(target=False) == (
        "<time datetime=\"2026-09-06\"><b>today</b></time>"
    )


def test_time_rejects_flow_content():
    class Page(HtmlBuilder):
        def main(self, root):
            root.time().div()

    with pytest.raises(ValueError, match="'div' not allowed as child of 'time'"):
        Page().create()
