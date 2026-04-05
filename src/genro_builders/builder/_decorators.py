# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Public decorator API for defining builder grammars.

Decorators:
    element   -- pure schema element (body must be empty ``...``).
    abstract  -- abstract element for inheritance only (``@``-prefixed).
    component -- composite structure with handler body (lazy expansion).
    data_element -- data infrastructure element (preprocessor body).

Internal:
    _is_empty_body -- bytecode check for empty function bodies.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import BagBuilderBase


# ---------------------------------------------------------------------------
# Empty body detection
# ---------------------------------------------------------------------------

def _ref_empty_body(self): ...


def _ref_empty_body_with_docstring(self):
    """docstring"""
    ...


_EMPTY_BODY_BYTECODE = _ref_empty_body.__code__.co_code
_EMPTY_BODY_DOCSTRING_BYTECODE = _ref_empty_body_with_docstring.__code__.co_code


def _is_empty_body(func: Callable) -> bool:
    """Check if function body is empty (just ... or docstring + ...)."""
    code = func.__code__.co_code
    return code in (_EMPTY_BODY_BYTECODE, _EMPTY_BODY_DOCSTRING_BYTECODE)


# ---------------------------------------------------------------------------
# @element
# ---------------------------------------------------------------------------

def element(
    tags: str | tuple[str, ...] | None = None,
    sub_tags: str | tuple[str, ...] | None = None,
    parent_tags: str | None = None,
    inherits_from: str | None = None,
    _meta: dict[str, Any] | None = None,
) -> Callable:
    """Decorator to mark a method as element handler.

    Args:
        tags: Tag names this method handles. If None, uses method name.
        sub_tags: Valid child tags with cardinality. Syntax:
            'a,b,c'     -> a, b, c each exactly once
            'a[],b[]'   -> a and b any number of times
            'a[2],b[0:]' -> a exactly twice, b zero or more
            '' (empty)  -> no children allowed (void element)
        parent_tags: Valid parent tags (comma-separated). If specified,
            element can only be placed inside one of these parents.
        inherits_from: Abstract element name to inherit sub_tags from.
        _meta: Dict of metadata for renderers/compilers (e.g.
            compile_class, compile_module, renderer_svg_style).

    Example:
        @element(sub_tags='header,content[],footer')
        def page(self): ...

        @element(
            sub_tags='child',
            _meta={'compile_module': 'textual.containers', 'compile_class': 'Container'},
        )
        def container(self): ...

        @element(parent_tags='ul,ol')  # can only be inside ul or ol
        def li(self): ...
    """
    def decorator(func: Callable) -> Callable:
        # Elements MUST have empty body (ellipsis only)
        if not _is_empty_body(func):
            raise ValueError(
                f"@element '{func.__name__}' must have empty body (...) - "
                "use @component for elements with logic"
            )

        func._decorator = {  # type: ignore[attr-defined]
            k: v
            for k, v in {
                "tags": tags,
                "sub_tags": sub_tags,
                "parent_tags": parent_tags,
                "inherits_from": inherits_from,
                "_meta": _meta,
            }.items()
            if v is not None
        }
        return func

    return decorator


# ---------------------------------------------------------------------------
# @abstract
# ---------------------------------------------------------------------------

def abstract(
    sub_tags: str | tuple[str, ...] = "",
    parent_tags: str | tuple[str, ...] | None = None,
    inherits_from: str | None = None,
    _meta: dict[str, Any] | None = None,
) -> Callable:
    """Decorator to define an abstract element (for inheritance only).

    Abstract elements are stored with '@' prefix and cannot be instantiated.
    They define sub_tags/parent_tags that can be inherited by concrete elements.

    Args:
        sub_tags: Valid child tags with cardinality (see element decorator).
        parent_tags: Valid parent tags with cardinality.
        inherits_from: Comma-separated list of abstract names to inherit from.
        _meta: Dict of metadata for renderers/compilers.

    Example:
        @abstract(sub_tags='span,a,em,strong')
        def phrasing(self): ...

        @element(inherits_from='@phrasing')
        def p(self): ...

        @abstract(
            sub_tags='child',
            _meta={'compile_module': 'textual.containers'},
        )
        def base_container(self): ...
    """
    def decorator(func: Callable) -> Callable:
        result: dict[str, Any] = {
            "abstract": True,
            "sub_tags": sub_tags,
            "inherits_from": inherits_from or "",
        }
        if parent_tags is not None:
            result["parent_tags"] = parent_tags
        if _meta:
            result["_meta"] = _meta
        func._decorator = result  # type: ignore[attr-defined]
        return func

    return decorator


# ---------------------------------------------------------------------------
# @component
# ---------------------------------------------------------------------------

def component(
    tags: str | tuple[str, ...] | None = None,
    sub_tags: str | tuple[str, ...] | None = None,
    parent_tags: str | None = None,
    builder: type[BagBuilderBase] | None = None,
    based_on: str | None = None,
    _meta: dict[str, Any] | None = None,
    slots: list[str] | None = None,
) -> Callable:
    """Decorator to mark a method as component handler.

    Components are composite structures that receive a new Bag, populate it,
    and return it. The populated bag becomes the node's value.

    Unlike @element, @component REQUIRES a method body (ellipsis not allowed).
    The handler receives a fresh Bag as first parameter (after self) and
    should populate it with child elements.

    Args:
        tags: Tag names this component handles. If None, uses method name.
        sub_tags: Valid child tags AFTER the component is created. Controls
            return behavior of the component call:
            - '' (empty string): Closed/leaf component, returns parent bag
              (for chaining at same level)
            - defined or None: Open container, returns internal bag
              (for adding children to the component)
        parent_tags: Valid parent tags (comma-separated). If specified,
            component can only be placed inside one of these parents.
        builder: Optional builder class for the component's internal bag.
            If not specified, uses the same builder class as parent.
        _meta: Dict of metadata for renderers/compilers.
        slots: List of named slot names. When present, the component call
            returns a ComponentProxy with slot Bags accessible as attributes.
            The handler body should return a dict mapping slot names to
            destination Bags where slot content will be mounted.

    Handler signature (without slots):
        def handler(self, component: Bag, **kwargs) -> None:
            # 'component' is the component's internal Bag to populate
            # Body is called ONLY at compile time (lazy expansion)

    Handler signature (with slots):
        def handler(self, component: Bag, **kwargs) -> dict[str, Bag]:
            # Return dict mapping slot name -> destination Bag
            # Slot content is mounted into destination Bags at compile time

    Example - Closed component (sub_tags=''):
        @component(sub_tags='')
        def login_form(self, component: Bag, **kwargs):
            component.input(name='username')
            component.input(name='password')
            component.button('Login')

        page.login_form()
        page.other_element()  # continues at same level

    Example - Open component (sub_tags defined):
        @component(sub_tags='item')
        def mylist(self, component: Bag, title='', **kwargs):
            component.header(title=title)

        lst = page.mylist(title='My List')
        lst.item('First')
        lst.item('Second')
    """
    def decorator(func: Callable) -> Callable:
        # Components MUST have a real body (not ellipsis)
        if _is_empty_body(func):
            raise ValueError(
                f"@component '{func.__name__}' must have a body - ellipsis (...) not allowed"
            )

        func._decorator = {  # type: ignore[attr-defined]
            k: v
            for k, v in {
                "component": True,
                "tags": tags,
                "sub_tags": sub_tags,
                "parent_tags": parent_tags,
                "builder": builder,
                "based_on": based_on,
                "_meta": _meta,
                "slots": slots,
            }.items()
            if v is not None
        }
        return func

    return decorator


# ---------------------------------------------------------------------------
# @data_element
# ---------------------------------------------------------------------------

def data_element(
    tags: str | tuple[str, ...] | None = None,
) -> Callable:
    """Decorator for data infrastructure elements.

    Data elements have a preprocessor body that returns (path, attrs_dict).
    They are transparent in sub_tags validation and NOT materialized in built.

    The handler body receives the raw arguments and returns a tuple:
        (path, attrs_dict) where path is the data path (None for controllers)
        and attrs_dict is a dict of attributes.

    Args:
        tags: Tag names this method handles. If None, uses method name.
    """
    def decorator(func: Callable) -> Callable:
        if _is_empty_body(func):
            raise ValueError(
                f"@data_element '{func.__name__}' must have a body"
            )
        func._decorator = {  # type: ignore[attr-defined]
            "data_element": True,
            "tags": tags,
        }
        return func

    return decorator
