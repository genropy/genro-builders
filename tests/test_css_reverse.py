# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the CSS reverse: parser wrapper smoke + visitor + classmethods."""
from __future__ import annotations

import pytest

pytest.importorskip("tree_sitter_css")

from genro_builders.contrib.css._reverse import _parse_css  # noqa: E402


def test_parse_css_returns_stylesheet_root():
    root = _parse_css(".foo { color: red; }")
    assert root.type == "stylesheet"


def test_parse_css_returns_empty_stylesheet_for_blank_source():
    root = _parse_css("")
    assert root.type == "stylesheet"
    assert root.named_child_count == 0


def test_parse_css_handles_at_rules():
    root = _parse_css("@media (max-width: 600px) { .a { width: 100%; } }")
    assert root.type == "stylesheet"
    kinds = [c.type for c in root.named_children]
    assert "media_statement" in kinds
