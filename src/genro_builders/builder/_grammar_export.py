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


def _meta_copy(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    """Shallow-copy ``_meta``. Return ``None`` if empty."""
    return dict(meta) if meta else None


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
    classmethod ``to_grammar`` on ``BuilderBase`` handles I/O.

    Sections are always present (empty dict if no entries). Top-level
    keys are emitted in this order:

    1. ``document_format``
    2. ``grammar``
    3. ``abstracts``
    4. ``elements``

    Sub-builders and data-elements are ordinary elements marked in their
    ``_meta`` (``subbuilder`` / ``data_element``, plus ``render_tag`` /
    ``render_attributes`` for a boundary envelope), so they appear in the
    ``elements`` section with that ``_meta`` — no separate section.

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

    elements_raw: dict[str, dict[str, Any]] = {}
    elements_order: list[str] = []
    for node in schema.get_nodes(
        condition=lambda n: not n.label.startswith("_")
    ):
        elements_raw[node.label] = _element_form(node)
        elements_order.append(node.label)

    document: dict[str, Any] = {
        "document_format": {
            "name": FORMAT_NAME,
            "version": FORMAT_VERSION,
        },
        "grammar": {
            "name": cls._name,  # type: ignore[attr-defined]
            "version": None,
            "title": None,
            "description": None,
        },
        "abstracts": _section_topologically_sorted(
            abstracts_raw, abstracts_order
        ),
        "elements": _section_topologically_sorted(
            elements_raw, elements_order
        ),
    }
    return document
