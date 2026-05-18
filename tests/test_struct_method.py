# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests per il decoratore @struct_method (sotto-step 2: solo metadata).

Dispatch sul bag testato nel sotto-step 3.
"""
from __future__ import annotations

import inspect

import pytest

from genro_builders import struct_method


def test_struct_method_marks_function():
    @struct_method
    def block(pane, x):
        pane.div(value=x)

    assert hasattr(block, "_decorator")
    assert block._decorator.get("struct_method") is True


def test_struct_method_requires_body():
    """Body ellipsis should raise (body-bearing decorator)."""
    with pytest.raises(ValueError, match="must have a body"):
        @struct_method
        def empty(pane): ...


def test_struct_method_preserves_signature():
    @struct_method
    def block(pane, x, y=1, **kw):
        pane.div(x=x, y=y)

    sig = inspect.signature(block)
    params = list(sig.parameters.keys())
    assert params == ["pane", "x", "y", "kw"]


def test_struct_method_importable_top_level():
    """`from genro_builders import struct_method` must work."""
    from genro_builders import struct_method as sm
    assert sm is struct_method
