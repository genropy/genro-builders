# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Grammar semantics must be identical on both element-creation entry
points: a node (``body.div(...)``) and a bag (``root.div(...)``).

The runnable behaviours (sub-builder switch, data-element field mapping)
are covered by the examples ``no_data/08_root_dispatch`` and
``with_logic/03_root_logic`` through the examples runner. This module
covers the error contract, which an example cannot ship: ``node_id``
uniqueness is enforced no matter which entry point creates the node.
"""
from __future__ import annotations

import pytest

from genro_builders.contrib.html import HtmlBuilder


def test_duplicate_node_id_on_root_raises():
    class Page(HtmlBuilder):
        def main(self, root):
            root.div(node_id="dup")
            root.div(node_id="dup")

    page = Page()
    with pytest.raises(ValueError, match="dup"):
        page.create()


def test_duplicate_node_id_on_node_raises():
    class Page(HtmlBuilder):
        def main(self, root):
            body = root.body()
            body.div(node_id="dup")
            body.div(node_id="dup")

    page = Page()
    with pytest.raises(ValueError, match="dup"):
        page.create()


def test_duplicate_node_id_across_entry_points_raises():
    class Page(HtmlBuilder):
        def main(self, root):
            body = root.body()
            body.div(node_id="dup")     # node path
            root.div(node_id="dup")     # bag path: same builder namespace

    page = Page()
    with pytest.raises(ValueError, match="dup"):
        page.create()
