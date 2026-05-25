# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Export a builder's `_class_schema` to a `builder_grammar` document.

The neutral JSON format produced here is the runtime contract between
the Python builder (producer) and consumers in other environments
(JavaScript builder, future `from_grammar` Python loader, downstream
transpilers).

The format is specified in `GRAMMAR_FORMAT.md`, co-located with this
module. This module is the **producer** side: it reads a builder
class's `_class_schema` Bag (populated by `__init_subclass__`) and
returns a dict that, when serialised with `json.dumps`, matches the
spec.

Exports:
    _class_schema_to_grammar_document: build the document dict.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

FORMAT_NAME = "builder_grammar"
FORMAT_VERSION = "1.0"


def _topological_sort(
    keys: list[str],
    get_deps: Callable[[str], list[str]],
) -> list[str]:
    """Return ``keys`` ordered so that each key comes after its deps.

    Dependencies returned by ``get_deps`` that are not in ``keys`` are
    treated as external (already emitted in another section) and
    ignored for ordering purposes.

    Ties break on the original insertion order of ``keys``: keys that
    are independent (no internal deps) keep their relative order.

    The implementation is Kahn's algorithm with an FIFO queue that
    preserves insertion order among ready nodes.
    """
    keys_set = set(keys)
    indegree: dict[str, int] = dict.fromkeys(keys, 0)
    edges: dict[str, list[str]] = {k: [] for k in keys}
    for k in keys:
        for dep in get_deps(k):
            if dep in keys_set and dep != k:
                edges[dep].append(k)
                indegree[k] += 1

    ready = [k for k in keys if indegree[k] == 0]
    out: list[str] = []
    while ready:
        # FIFO -> keep insertion order among ready nodes
        k = ready.pop(0)
        out.append(k)
        for succ in edges[k]:
            indegree[succ] -= 1
            if indegree[succ] == 0:
                ready.append(succ)

    if len(out) != len(keys):
        # Cycle in inherits_from. Should not happen in practice but
        # report explicitly rather than emit a partial document.
        remaining = [k for k in keys if k not in out]
        raise ValueError(
            f"Cycle in inherits_from chain involving: {remaining}"
        )
    return out


def _parse_inherits_from(raw: Any) -> list[str]:
    """Return the list of parent names declared in ``raw``."""
    if not raw:
        return []
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def _meta_copy(meta: Any) -> Any:
    """Shallow-copy `_meta` pass-through. Return `None` if empty."""
    if not meta:
        return None
    if isinstance(meta, dict):
        return dict(meta)
    return meta


def _abstract_form(node: Any) -> dict[str, Any]:
    """JSON form of an abstract node."""
    inherits_from = node.get_attr("inherits_from") or None
    return {
        "doc": node.get_attr("documentation"),
        "sub_tags": node.get_attr("sub_tags"),
        "parent_tags": node.get_attr("parent_tags"),
        "inherits_from": inherits_from,
        "_meta": _meta_copy(node.get_attr("_meta")),
    }


def _wrapper_method_for(cls: type, sub_name: str) -> Any:
    """Locate a ``wrapper_<sub_name>`` method on ``cls.__mro__``.

    Walks the MRO via ``__dict__`` to bypass ``__getattr__`` (which
    intercepts unknown attribute access on the builder to dispatch
    grammar tags). Returns the function (unbound), or ``None`` if no
    host class in the MRO declares it.
    """
    attr_name = f"wrapper_{sub_name}"
    for klass in cls.__mro__:
        if attr_name in klass.__dict__:
            return klass.__dict__[attr_name]
    return None


def _subbuilder_form_from_meta(
    method: Any,
    meta: dict[str, Any],
    host_instance: Any,
) -> dict[str, Any]:
    """JSON form of a subbuilder from the decorator's ``_subbuilder_meta``.

    Boundary markup (``wrap_tag`` + ``wrap_attrs``) is harvested by
    invoking the host's ``wrapper_<sub_name>`` method if declared.
    """
    sub_name = meta.get("subbuilder_name")
    wrap_tag = None
    wrap_attrs: dict[str, Any] | None = None
    wrapper_method = _wrapper_method_for(type(host_instance), sub_name) if sub_name else None
    if wrapper_method is not None:
        wrapper_spec = wrapper_method(host_instance)
        wrap_tag = wrapper_spec.get("tag")
        wrap_attrs = dict(wrapper_spec.get("attrs") or {}) or None
    return {
        "doc": method.__doc__,
        "builder_name": sub_name,
        "parent_tags": meta.get("parent_tags"),
        "wrap_tag": wrap_tag,
        "wrap_attrs": wrap_attrs,
        "_meta": _meta_copy(meta.get("_meta")),
    }


def _collect_subbuilders(cls: type) -> dict[str, dict[str, Any]]:
    """Walk ``cls.__mro__`` and collect ``@subbuilder``-decorated methods.

    The subbuilder decorator attaches ``_subbuilder_meta`` on the
    wrapper it installs on the class; we discover them by attribute
    inspection rather than via the schema (subbuilders are not part of
    ``_class_schema`` since the autonomous dispatch refactor).

    Returns a dict ``{tag_name: form}`` in MRO walk order (subclasses
    win over base classes when tag names collide).
    """
    host_instance = cls()
    collected: dict[str, dict[str, Any]] = {}
    for klass in reversed(cls.__mro__):
        for attr_name, obj in klass.__dict__.items():
            meta = getattr(obj, "_subbuilder_meta", None)
            if meta is None:
                continue
            tag_name = meta.get("tag_name") or attr_name
            collected[tag_name] = _subbuilder_form_from_meta(obj, meta, host_instance)
    return collected


def _element_form(node: Any) -> dict[str, Any]:
    """JSON form of an element node."""
    inherits_from = node.get_attr("inherits_from") or None
    return {
        "doc": node.get_attr("documentation"),
        "sub_tags": node.get_attr("sub_tags"),
        "parent_tags": node.get_attr("parent_tags"),
        "inherits_from": inherits_from,
        "attributes": None,
        "_meta": _meta_copy(node.get_attr("_meta")),
    }


def _data_element_form(node: Any) -> dict[str, Any]:
    """JSON form of a data_element node."""
    return {
        "doc": node.get_attr("documentation"),
    }


def _section_topologically_sorted(
    raw_items: dict[str, dict[str, Any]],
    insertion_order: list[str],
) -> dict[str, dict[str, Any]]:
    """Topologically sort a section's items by their `inherits_from`.

    `raw_items` keeps the per-key forms produced by `_*_form`.
    `insertion_order` is the original order of keys as seen in the
    schema. Returned dict has the same keys, reordered.

    Dependencies that point outside this section (typical case:
    elements inherit from abstracts) are ignored — only intra-section
    edges constrain the order.
    """
    def get_deps(k: str) -> list[str]:
        # Read `inherits_from` if the form declares one. Subbuilders
        # and data_elements have no inheritance, so the call returns
        # the empty list naturally.
        form = raw_items[k]
        return _parse_inherits_from(form.get("inherits_from"))

    ordered = _topological_sort(insertion_order, get_deps)
    return {k: raw_items[k] for k in ordered}


def _class_schema_to_grammar_document(cls: type) -> dict[str, Any]:
    """Build the `builder_grammar` document for ``cls``.

    Reads ``cls._class_schema`` and returns a dict ready to be
    serialised with ``json.dumps``. Does not write to disk; the
    classmethod ``to_grammar`` on ``BagBuilderBase`` handles I/O.

    Sections are always present (empty dict if no entries). Top-level
    keys are emitted in this order:

    1. ``document_format``
    2. ``grammar``
    3. ``abstracts``
    4. ``subbuilders``
    5. ``elements``
    6. ``data_elements``

    Within each section, entries are topologically sorted by their
    ``inherits_from`` references (insertion-order on ties).
    """
    schema = cls._class_schema  # type: ignore[attr-defined]

    abstracts_raw: dict[str, dict[str, Any]] = {}
    abstracts_order: list[str] = []
    abstracts_bag = schema["_abstracts"]
    for node in abstracts_bag:
        abstracts_raw[node.label] = _abstract_form(node)
        abstracts_order.append(node.label)

    subbuilders_raw = _collect_subbuilders(cls)
    subbuilders_order = list(subbuilders_raw.keys())
    elements_raw: dict[str, dict[str, Any]] = {}
    elements_order: list[str] = []
    data_elements_raw: dict[str, dict[str, Any]] = {}
    data_elements_order: list[str] = []

    for node in schema.get_nodes(
        condition=lambda n: not n.label.startswith("_")
    ):
        if node.get_attr("is_data_element"):
            data_elements_raw[node.label] = _data_element_form(node)
            data_elements_order.append(node.label)
        else:
            elements_raw[node.label] = _element_form(node)
            elements_order.append(node.label)

    document: dict[str, Any] = {
        "document_format": {
            "name": FORMAT_NAME,
            "version": FORMAT_VERSION,
        },
        "grammar": {
            "name": getattr(cls, "_name", None),
            "version": None,
            "title": None,
            "description": None,
        },
        "abstracts": _section_topologically_sorted(
            abstracts_raw, abstracts_order
        ),
        "subbuilders": _section_topologically_sorted(
            subbuilders_raw, subbuilders_order
        ),
        "elements": _section_topologically_sorted(
            elements_raw, elements_order
        ),
        "data_elements": _section_topologically_sorted(
            data_elements_raw, data_elements_order
        ),
    }
    return document
