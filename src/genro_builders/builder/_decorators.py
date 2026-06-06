# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Public decorator API for defining builder grammars.

Declarative decorators (``@element``, ``@abstract``) ignore the
function body: they replace the decorated function with an inert
``_DeclarativeMarker`` carrying only what the framework reads
(``__name__``, ``__doc__``, ``_decorator``). Any body the user wrote
is therefore unreachable.

There is no separate ``@subbuilder`` or ``@data_element`` decorator.
Both are ordinary ``@element`` declarations marked in their ``_meta``:
``_meta={"subbuilder": "<dialect>", ...}`` for a dialect boundary (with
optional ``render_tag`` / ``render_attributes`` for the envelope), and
``_meta={"data_element": True}`` for the three data-elements
(``data_setter`` / ``data_formula`` / ``data_controller``). They flow
through the same schema and the same ``_command_on_node`` dispatch as
plain elements; the element's ``_meta`` rides onto the node and every
reader queries it via ``node._get_meta(...)``.

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
# Declarative marker (used by @element, @abstract)
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
        func: Callable | None = None,
    ) -> None:
        self.__name__ = name
        self.__doc__ = doc
        self._decorator = decorator
        # Keep the original function for signature introspection only
        # (call-argument validation reads it via ``_extract_validators_from_
        # signature``). The marker stays inert — no ``__call__`` — so direct
        # invocation of ``cls.<tag>()`` still raises TypeError.
        self._func = func


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
            "is ignored. Declarative decorators only read the signature.",
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
            'a,b,c'     -> a, b, c each any number of times (0..N)
            'a[2],b[0:]' -> a exactly twice, b zero or more
            '' (empty)  -> no children allowed (void element)
            '*'         -> any tag allowed (catch-all)
            A bare name is unbounded; 'foo[]' is invalid (raises
            ValueError) -- use 'foo' for 0..N or 'foo[n]' for a count.
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
        return _DeclarativeMarker(func.__name__, func.__doc__, info, func)

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

    Abstract elements live in a dedicated ``_abstracts`` sub-bag of the
    class schema (bare names, no '@' prefix) and cannot be instantiated.
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
        return _DeclarativeMarker(func.__name__, func.__doc__, info, func)

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

    Body must not be empty (ellipsis): a struct-method carries real logic.
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


# ---------------------------------------------------------------------------
# @component
# ---------------------------------------------------------------------------

def component(
    tags: str | tuple[str, ...] | None = None,
    sub_tags: str | tuple[str, ...] | None = None,
    parent_tags: str | None = None,
    inherits_from: str | None = None,
    _meta: dict[str, Any] | None = None,
) -> Callable:
    """Decorator: a grammar element whose body builds a reusable structure.

    Unlike ``@element`` (declarative, empty body, dropped from the class),
    a component CARRIES a body: it populates a fresh source (a
    ``new_root``) and that subtree is the component's expansion. The body
    is therefore kept callable on the class — it is not turned into an
    inert marker. The element enters the schema like any other, marked
    ``_meta['component'] = True`` so the renderer recognises it and, at
    render time, builds a ``new_root``, runs the body on it, and uses the
    resulting source as the node's content.

    The same arguments as ``@element`` (``tags``, ``sub_tags``,
    ``parent_tags``, ``inherits_from``, ``_meta``) place it in the grammar.
    A same-named plain element is overridden by the component.

    Example::

        @component
        def product_card(self, root):
            row = root.div(class_="card")
            row.h3("^.?name")
            row.p("^.?price", class_="price")
    """
    def _mark(func: Callable) -> Callable:
        merged_meta = {"component": True, **(_meta or {})}
        info: dict[str, Any] = {"_meta": merged_meta}
        for key, value in (
            ("tags", tags),
            ("sub_tags", sub_tags),
            ("parent_tags", parent_tags),
            ("inherits_from", inherits_from),
        ):
            if value is not None:
                info[key] = value
        func._decorator = info  # type: ignore[attr-defined]
        return func

    # Bare ``@component`` (no parentheses): ``tags`` holds the function.
    if callable(tags):
        func, tags = tags, None
        return _mark(func)

    return _mark
