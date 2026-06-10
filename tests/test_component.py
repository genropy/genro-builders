# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Component error contracts (area CMP).

The runnable behaviour (single component, explicit params, reuse) is
covered by the example ``with_data/07_address_block`` through the
examples runner. This module covers what an example cannot ship: the
tree-not-forest violation raises.
"""
from __future__ import annotations

import pytest

from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder


def test_component_forest_raises():
    class Components:
        @component
        def twin_blocks(self, root):
            root.div("one")
            root.div("two")          # second root: a forest

    class Page(HtmlBuilder, Components):
        def main(self, root):
            root.body().twin_blocks()

    page = Page()
    page.create()                    # expansion happens at render time
    with pytest.raises(ValueError, match="tree, not a forest"):
        page.render()


def test_component_empty_expansion_raises():
    class Components:
        @component
        def nothing(self, root):
            pass                     # zero roots: not a tree either

    class Page(HtmlBuilder, Components):
        def main(self, root):
            root.body().nothing()

    page = Page()
    page.create()
    with pytest.raises(ValueError, match="tree, not a forest"):
        page.render()
