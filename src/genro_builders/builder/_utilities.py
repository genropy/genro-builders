# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Internal utility functions for type checking, annotation parsing,
sub_tags/parent_tags spec parsing, and decorated-method extraction.

All functions are module-private (prefixed with ``_``) and consumed by
the builder package internals. Some are re-exported in ``__init__.py``
for backward-compatible test imports.
"""

from __future__ import annotations

import inspect
import numbers
import re
import sys
import types
from collections.abc import Callable
from typing import (
    Annotated,
    Any,
    Literal,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

# ---------------------------------------------------------------------------
# Annotated type splitting
# ---------------------------------------------------------------------------

def _split_annotated(tp: Any) -> tuple[Any, list]:
    """Split Annotated type into base type and validators.

    Handles Optional[Annotated[T, ...]] which appears as Union[Annotated[T, ...], None].
    """
    if get_origin(tp) is Annotated:
        base, *meta = get_args(tp)
        validators = [m for m in meta if callable(m)]
        return base, validators

    # Handle Optional[Annotated[...]] -> Union[Annotated[...], None]
    if get_origin(tp) is Union:
        args = get_args(tp)
        # Check if it's Optional (Union with NoneType)
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            inner = non_none_args[0]
            if get_origin(inner) is Annotated:
                base, *meta = get_args(inner)
                validators = [m for m in meta if callable(m)]
                return base, validators

    return tp, []


# ---------------------------------------------------------------------------
# Type checking
# ---------------------------------------------------------------------------

def _check_type(value: Any, tp: Any) -> bool:
    """Check if value matches the type annotation."""
    tp, _ = _split_annotated(tp)

    origin = get_origin(tp)
    args = get_args(tp)

    if tp is Any:
        return True

    if tp is type(None):
        return value is None

    if origin is Literal:
        return value in args

    if origin is types.UnionType:
        return any(_check_type(value, t) for t in args)

    if origin is Union:
        return any(_check_type(value, t) for t in args)

    if origin is None:
        if tp is float and isinstance(value, numbers.Number):
            return True
        try:
            return isinstance(value, tp)
        except TypeError:
            return True

    if origin is list:
        if not isinstance(value, list):
            return False
        if not args:
            return True
        t_item = args[0]
        return all(_check_type(v, t_item) for v in value)

    if origin is dict:
        if not isinstance(value, dict):
            return False
        if not args:
            return True
        k_t, v_t = args[0], args[1] if len(args) > 1 else Any
        return all(_check_type(k, k_t) and _check_type(v, v_t) for k, v in value.items())

    if origin is tuple:
        if not isinstance(value, tuple):
            return False
        if not args:
            return True
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_check_type(v, args[0]) for v in value)
        return len(value) == len(args) and all(
            _check_type(v, t) for v, t in zip(value, args, strict=True)
        )

    if origin is set:
        if not isinstance(value, set):
            return False
        if not args:
            return True
        t_item = args[0]
        return all(_check_type(v, t_item) for v in value)

    try:
        return isinstance(value, origin)
    except TypeError:
        return True


# ---------------------------------------------------------------------------
# Signature / validator extraction
# ---------------------------------------------------------------------------

def _extract_validators_from_signature(fn: Callable) -> dict[str, tuple[Any, list, Any]]:
    """Extract type hints with validators from function signature."""
    skip_params = {
        "self",
        "build_where",
        "node_tag",
        "node_label",
        "node_position",
        "component",  # first param of @component methods
        "comp",  # short form for component param
    }

    try:
        hints = get_type_hints(fn, include_extras=True)
    except Exception:
        return {}

    result = {}
    sig = inspect.signature(fn)

    for name, param in sig.parameters.items():
        if name in skip_params:
            continue
        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue

        tp = hints.get(name)
        if tp is None:
            continue

        base, validators = _split_annotated(tp)
        result[name] = (base, validators, param.default)

    return result


# ---------------------------------------------------------------------------
# Sub-tags and parent-tags spec parsing
# ---------------------------------------------------------------------------

def _parse_parent_tags_spec(spec: str) -> set[str]:
    """Parse parent_tags spec into set of valid parent tag names.

    Simple comma-separated list of tag names (no cardinality).

    Args:
        spec: Comma-separated list of tag names, e.g. "div, span, section".

    Returns:
        Set of valid parent tag names.
    """
    return {tag.strip() for tag in spec.split(",") if tag.strip()}


def _parse_sub_tags_spec(spec: str) -> dict[str, tuple[int, int]] | str:
    """Parse sub_tags spec into dict of {tag: (min, max)} or "*" for any.

    Semantics:
        ""       -> leaf element (no children allowed) - returns empty dict
        "*"      -> accepts any children (no validation) - returns "*"
        "foo"    -> accepts only "foo" children

    Cardinality syntax:
        foo      -> any number 0..N (min=0, max=sys.maxsize)
        foo[1]   -> exactly 1 (min=1, max=1)
        foo[3]   -> exactly 3 (min=3, max=3)
        foo[0:]  -> 0 or more (min=0, max=sys.maxsize)
        foo[:2]  -> 0 to 2 (min=0, max=2)
        foo[1:3] -> 1 to 3 (min=1, max=3)
        foo[]    -> ERROR (invalid syntax)

    Returns:
        "*" if spec is "*" (accepts any children)
        dict of {tag: (min, max)} otherwise
    """
    # Handle wildcard - accepts any children
    if spec == "*":
        return "*"

    result: dict[str, tuple[int, int]] = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        # Try [min:max] format first
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\[(\d*):(\d*)\]$", item)
        if match:
            tag = match.group(1)
            min_val = int(match.group(2)) if match.group(2) else 0
            max_val = int(match.group(3)) if match.group(3) else sys.maxsize
            result[tag] = (min_val, max_val)
            continue
        # Try [n] format (exactly n)
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\[(\d+)\]$", item)
        if match:
            tag = match.group(1)
            n = int(match.group(2))
            result[tag] = (n, n)
            continue
        # Check for invalid [] format
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\[\]$", item)
        if match:
            raise ValueError(
                f"Invalid sub_tags syntax: '{item}' - use 'foo' for 0..N or 'foo[n]' for exact count"
            )
        # Plain tag name (0..N)
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)$", item)
        if match:
            tag = match.group(1)
            result[tag] = (0, sys.maxsize)
    return result


# ---------------------------------------------------------------------------
# Decorated-method extraction
# ---------------------------------------------------------------------------

def _decorated_method_info(
    name: str, obj: Any,
) -> tuple[list[str], str | None, Any, dict]:
    """Build (tag_list, method_name, obj, decorator_info) for a decorated method."""
    decorator_info = obj._decorator
    if decorator_info.get("abstract"):
        return [f"@{name}"], None, obj, decorator_info
    elif decorator_info.get("data_element"):
        tag_list: list[str] = [] if name.startswith("_") else [name]
        tags_raw = decorator_info.get("tags")
        if tags_raw:
            if isinstance(tags_raw, str):
                tag_list.extend(t.strip() for t in tags_raw.split(",") if t.strip())
            else:
                tag_list.extend(tags_raw)
        handler_name = f"_dtel_{tag_list[0]}"
        return tag_list, handler_name, obj, decorator_info
    elif decorator_info.get("component"):
        tag_list: list[str] = [] if name.startswith("_") else [name]
        tags_raw = decorator_info.get("tags")
        if tags_raw:
            if isinstance(tags_raw, str):
                tag_list.extend(t.strip() for t in tags_raw.split(",") if t.strip())
            else:
                tag_list.extend(tags_raw)
        handler_name = f"_comp_{tag_list[0]}"
        return tag_list, handler_name, obj, decorator_info
    else:
        tag_list = [] if name.startswith("_") else [name]
        tags_raw = decorator_info.get("tags")
        if tags_raw:
            if isinstance(tags_raw, str):
                tag_list.extend(t.strip() for t in tags_raw.split(",") if t.strip())
            else:
                tag_list.extend(tags_raw)
        return tag_list, None, obj, decorator_info


def _pop_decorated_methods(cls: type, builder_base: type):
    """Remove and yield decorated methods from cls and its mixin bases.

    Collects @element, @abstract, and @component methods from:
    1. The class itself (cls.__dict__) -- removed with delattr
    2. Mixin bases in MRO that are not BagBuilderBase subclasses

    Methods defined directly on cls take priority over mixin methods.
    Mixin methods are NOT removed from their defining class.

    Args:
        cls: The class being processed.
        builder_base: The BagBuilderBase class (passed to avoid circular import).
    """
    seen: set[str] = set()

    for name, obj in list(cls.__dict__.items()):
        if hasattr(obj, "_decorator"):
            seen.add(name)
            delattr(cls, name)
            yield _decorated_method_info(name, obj)

    for base in cls.__mro__:
        if base is cls or base is object:
            continue
        if base is builder_base:
            # Collect @data_element methods from BagBuilderBase
            for name, obj in list(base.__dict__.items()):
                if name in seen:
                    continue
                if hasattr(obj, "_decorator") and obj._decorator.get("data_element"):
                    seen.add(name)
                    yield _decorated_method_info(name, obj)
            continue
        if issubclass(base, builder_base):
            continue
        for name, obj in list(base.__dict__.items()):
            if name in seen:
                continue
            if hasattr(obj, "_decorator"):
                seen.add(name)
                yield _decorated_method_info(name, obj)
