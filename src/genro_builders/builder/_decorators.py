# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Public decorator API for defining builder grammars.

Declarative decorators (``@element``, ``@abstract``) ignore the
function body: they replace the decorated function with an inert
``_DeclarativeMarker`` carrying only what the framework reads
(``__name__``, ``__doc__``, ``_decorator``). Any body the user wrote
is therefore unreachable.

Body-bearing decorators (``@subbuilder``, ``@data_element``) keep the
original function so the framework can call it later.

Internal:
    _DeclarativeMarker -- inert wrapper for declarative decorators.
    _is_empty_body -- best-effort bytecode check, only used to emit
        a warning when a declarative body is non-empty (the body would
        be ignored anyway, so this is a UX hint, not a hard error).
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import Any

# ---------------------------------------------------------------------------
# Declarative marker (used by @element, @abstract, @subbuilder)
# ---------------------------------------------------------------------------

class _DeclarativeMarker:
    """Inert object returned by declarative decorators.

    Carries the metadata the framework needs (``__name__``, ``__doc__``,
    ``_decorator``) and nothing else. Not callable: any attempt to
    invoke ``cls.<tag>()`` directly raises ``TypeError``, which is
    intentional — the dialect dispatch goes through ``_bag_call`` and
    never invokes the original method.
    """

    def __init__(
        self,
        name: str,
        doc: str | None,
        decorator: dict[str, Any],
    ) -> None:
        self.__name__ = name
        self.__doc__ = doc
        self._decorator = decorator


# ---------------------------------------------------------------------------
# Empty body detection (best-effort, used only to warn)
# ---------------------------------------------------------------------------

def _ref_empty_body(self): ...


def _ref_empty_body_with_docstring(self):
    """docstring"""
    ...


_EMPTY_BODY_BYTECODE = _ref_empty_body.__code__.co_code
_EMPTY_BODY_DOCSTRING_BYTECODE = _ref_empty_body_with_docstring.__code__.co_code


def _is_empty_body(func: Callable) -> bool:
    """Best-effort check: is the function body just ``...`` (with optional docstring)?

    Compares ``co_code`` against two reference snippets. The check has
    known false positives — ``return <const>`` compiles to the same
    opcodes as a docstring followed by ``...``, because ``RETURN_CONST``
    is encoded by index in ``co_consts`` rather than by value. For
    declarative decorators this only powers a warning: the body is
    dropped regardless of the check's verdict, so a missed warning has
    no runtime impact.
    """
    code = func.__code__.co_code
    return code in (_EMPTY_BODY_BYTECODE, _EMPTY_BODY_DOCSTRING_BYTECODE)


def _warn_if_body_present(func: Callable, decorator_name: str) -> None:
    """Emit a UX hint when a declarative decorator wraps a non-empty body.

    Best-effort (see ``_is_empty_body``). When the check is uncertain
    we stay silent: the body is dropped anyway, so silence is safer
    than a noisy false positive.
    """
    if not _is_empty_body(func):
        warnings.warn(
            f"@{decorator_name} '{func.__name__}': the function body "
            "is ignored. Declarative decorators only read the signature; "
            "if you need a body, use @data_element or @subbuilder instead.",
            stacklevel=3,
        )


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
    def decorator(func: Callable) -> _DeclarativeMarker:
        _warn_if_body_present(func, "element")
        info = {
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
        return _DeclarativeMarker(func.__name__, func.__doc__, info)

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

        @element(inherits_from='phrasing')
        def p(self): ...

        @abstract(
            sub_tags='child',
            _meta={'compile_module': 'textual.containers'},
        )
        def base_container(self): ...
    """
    def decorator(func: Callable) -> _DeclarativeMarker:
        _warn_if_body_present(func, "abstract")
        info: dict[str, Any] = {
            "abstract": True,
            "sub_tags": sub_tags,
            "inherits_from": inherits_from or "",
        }
        if parent_tags is not None:
            info["parent_tags"] = parent_tags
        if _meta:
            info["_meta"] = _meta
        return _DeclarativeMarker(func.__name__, func.__doc__, info)

    return decorator


# ---------------------------------------------------------------------------
# @subbuilder
# ---------------------------------------------------------------------------

def subbuilder(
    builder_name: str,
    tags: str | tuple[str, ...] | None = None,
    parent_tags: str | None = None,
    wrap_tag: str | None = None,
    _meta: dict[str, Any] | None = None,
) -> Callable:
    """Decorator declaring a tag that opens a sub-builder (decision 2).

    The tag is part of the host dialect (e.g. ``<svg>`` inside HTML5),
    but from this node down the active builder is the dialect
    registered under ``builder_name``, not the host. The sub-builder
    governs its own ``sub_tags``; the host only declares
    ``parent_tags`` (where the sub-builder may be embedded).

    The target builder is identified by its canonical ``_name`` (see
    :attr:`BagBuilderBase.register`). Resolution is lazy: the framework
    looks the class up via :meth:`BagBuilderBase.get_builder_class`
    when the sub-builder is actually attached, not at decoration time.
    This removes import-circularity barriers between mutually-referencing
    dialect modules (HTML <-> SVG, etc.).

    Like ``@element`` and ``@abstract`` it is purely declarative: any
    function body the user writes is dropped, with a best-effort
    warning when the body is detected as non-empty.

    Currently the framework records the declaration in the schema but
    raises ``NotImplementedError`` at attach time (decision 2 is
    pending implementation — see ``_GrammarMixin._child``).

    Args:
        builder_name: Canonical ``_name`` of the Builder dialect active
            inside the subtree (e.g. ``"svg"``, ``"html"``).
        tags: Tag names this method handles. If None, uses method name.
        parent_tags: Valid parent tags in the host dialect.
        wrap_tag: Optional tag name that the render walker wraps around
            the sub-renderer's output (e.g. the SVG ``html`` subbuilder
            uses ``wrap_tag="foreignObject"`` so the runtime markup
            satisfies the SVG embedding rule). Skipped if ``None``.
        _meta: Dict of metadata for renderers/compilers.
    """
    if not isinstance(builder_name, str):
        raise TypeError(
            f"@subbuilder expects a builder name (str), got "
            f"{type(builder_name).__name__}: {builder_name!r}"
        )

    def decorator(func: Callable) -> Callable:
        # The body of an @subbuilder is a hook the framework can call
        # to customise the sub-builder attach. Empty body (``...``)
        # means "use the default delegation" — detected via
        # ``_is_empty_body``.
        info: dict[str, Any] = {
            "subbuilder": True,
            "subbuilder_name": builder_name,
            "tags": tags,
        }
        if parent_tags is not None:
            info["parent_tags"] = parent_tags
        if wrap_tag is not None:
            info["wrap_tag"] = wrap_tag
        if _meta:
            info["_meta"] = _meta
        func._decorator = info  # type: ignore[attr-defined]
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
    They are transparent in sub_tags validation and emit no markup at render time.

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


def struct_method(func_or_name):
    """Decorator: mark a handler method as a callable block invocable
    from any node via the bag's dispatch.

    Naming rules (legacy gnrwebstruct parity):
        @struct_method
        def widget(self, pane, ...): ...      # dispatch name: 'widget'

        @struct_method
        def iv_widget(self, pane, ...): ...   # dispatch name: 'widget'
                                              # (strip prefix before first '_')

        @struct_method('alias')
        def some_internal_name(self, pane, ...): ...  # dispatch name: 'alias'

    Body must not be empty (ellipsis); same convention as @data_element.
    """
    def _mark(func: Callable, explicit_name: str | None) -> Callable:
        if _is_empty_body(func):
            raise ValueError(
                f"@struct_method '{func.__name__}' must have a body"
            )
        func._decorator = {  # type: ignore[attr-defined]
            "struct_method": True,
            "name": explicit_name,
        }
        return func

    if isinstance(func_or_name, str):
        explicit = func_or_name

        def decorate(func: Callable) -> Callable:
            return _mark(func, explicit)

        return decorate

    return _mark(func_or_name, None)
