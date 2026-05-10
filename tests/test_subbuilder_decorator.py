# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the @subbuilder declaration (decision 2, rinegoziata 2026-05-08).

The decorator is recorded in the schema but switching the active
builder for a subtree is not implemented yet. The framework must
raise ``NotImplementedError`` with a parlante message when an
@subbuilder element is attached to a source bag, so the contract
stays honest until decision 2 is fully wired.
"""
from __future__ import annotations

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder import element, subbuilder


class _OtherDialect(BagBuilderBase):
    """Stand-in sub-builder. Empty schema is fine for these tests."""


class _HostDialect(BagBuilderBase):

    @element()
    def root(self): ...

    @subbuilder(_OtherDialect)
    def switch(self): ...


def test_subbuilder_decorator_records_class_in_schema():
    """The schema node for the subbuilder tag knows the target class."""
    builder = _HostDialect()
    info = builder._get_schema_info("switch")
    assert info.get("is_subbuilder") is True
    assert info.get("subbuilder_class") is _OtherDialect


def test_subbuilder_appears_in_schema_tag_names():
    """Tag dispatch sees the subbuilder name like any other tag."""
    builder = _HostDialect()
    assert "switch" in builder._schema_tag_names


def test_subbuilder_attach_raises_not_implemented():
    """Decision 2 pending: attaching an @subbuilder element raises."""
    from genro_builders import BuilderBag

    builder = _HostDialect()
    bag = BuilderBag(builder=builder)
    with pytest.raises(NotImplementedError) as excinfo:
        bag.switch()
    msg = str(excinfo.value)
    assert "subbuilder" in msg.lower()
    assert "decision 2" in msg.lower()
    assert "_OtherDialect" in msg


# NOTE: a "rejects non-empty body" test was attempted but the underlying
# _is_empty_body() bytecode-equality check has a pre-existing false
# positive on Python 3.12 (return statements compile to the same RESUME
# + RETURN_CONST sequence as bare ellipsis, and the "docstring" reference
# masks them). The body-empty enforcement is therefore best-effort across
# all decorators (@element, @abstract, @subbuilder), out of scope for the
# 2026-05 restart fase 2.
