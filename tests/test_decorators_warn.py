# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for declarative decorators (@element, @abstract, @subbuilder).

Declarative decorators replace the decorated function with an inert
``_DeclarativeMarker``: the body is dropped. A best-effort warning is
emitted when the decorator detects a non-empty body (the underlying
``_is_empty_body`` check has known false positives, so the absence of
a warning does NOT prove the body was empty — but when the warning
fires it is correct).
"""
from __future__ import annotations

import warnings

from genro_builders.builder import abstract, element, subbuilder
from genro_builders.builder._decorators import _DeclarativeMarker


def test_element_returns_declarative_marker():
    """@element drops the function and returns a marker object."""
    @element()
    def div(self): ...

    assert isinstance(div, _DeclarativeMarker)
    assert div.__name__ == "div"
    assert div._decorator == {}


def test_element_marker_is_not_callable():
    """The marker has no __call__, so direct invocation must fail."""
    @element()
    def div(self): ...

    try:
        div()
    except TypeError:
        return
    raise AssertionError("expected TypeError when calling a declarative marker")


def test_element_preserves_docstring_in_marker():
    """The marker exposes the original __doc__."""
    @element()
    def div(self):
        """Block-level container."""
        ...

    assert div.__doc__ == "Block-level container."


def test_abstract_returns_declarative_marker():
    @abstract(sub_tags="span,a")
    def phrasing(self): ...

    assert isinstance(phrasing, _DeclarativeMarker)
    assert phrasing._decorator["abstract"] is True
    assert phrasing._decorator["sub_tags"] == "span,a"


def test_subbuilder_attaches_decorator_metadata_to_function():
    """@subbuilder leaves the function alive (the body is an optional
    hook the framework can call to customise sub-builder attach) and
    tags it with the decorator info the framework reads from the schema."""
    @subbuilder("html")
    def switch(self): ...

    assert callable(switch)
    assert not isinstance(switch, _DeclarativeMarker)
    assert switch._decorator["subbuilder"] is True
    assert switch._decorator["subbuilder_name"] == "html"


def test_subbuilder_rejects_non_string_target():
    """Passing a class (or anything non-str) raises TypeError."""
    import pytest

    with pytest.raises(TypeError):
        @subbuilder(object)  # type: ignore[arg-type]
        def switch(self): ...


def test_element_warns_when_body_is_clearly_non_empty():
    """A multiline body must trip the best-effort check and warn."""
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")

        @element()
        def with_body(self):
            x = 1
            y = 2
            return x + y

    messages = [str(w.message) for w in recorded if "with_body" in str(w.message)]
    assert messages, "expected a warning citing 'with_body'"
    assert "ignored" in messages[0]


def test_element_does_not_warn_for_empty_body():
    """Empty body (just ...) must not produce a warning."""
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")

        @element()
        def empty(self): ...

    messages = [str(w.message) for w in recorded if "empty" in str(w.message)]
    assert not messages


def test_element_does_not_warn_for_docstring_plus_ellipsis():
    """Docstring + ... is the canonical empty body — no warning."""
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")

        @element()
        def with_doc(self):
            """A docstring is fine."""
            ...

    messages = [str(w.message) for w in recorded if "with_doc" in str(w.message)]
    assert not messages
