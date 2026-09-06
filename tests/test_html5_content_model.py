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
