# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""YamlRenderer — the shared ``yaml`` render mode.

YAML is another serialization of the same builder tree. Each node
yields a ``(tag, value)`` structure fragment; ``finalize`` folds the
top-level fragments into a nested Python dict and dumps it with PyYAML.

PyYAML is an optional dependency (extra ``[yaml]``): importing this
module never requires it (the import is guarded). Calling ``finalize``
without it raises a clear, actionable error.
"""

from __future__ import annotations

from typing import Any

try:
    import yaml as _pyyaml
except ImportError as exc:  # pragma: no cover - exercised only when extra missing
    _PYYAML_IMPORT_ERROR: ImportError | None = exc
    _pyyaml = None  # type: ignore[assignment]
else:
    _PYYAML_IMPORT_ERROR = None

from .base import RendererBase


class YamlRenderer(RendererBase):
    """Renderer of the shared ``yaml`` mode.

    Exposed by ``BuilderBase.renderer_yaml`` so every dialect can
    serialize its tree to YAML. Unlike XML/HTML/CSS (which emit text
    fragments), each node yields a *structure* fragment — a ``(tag,
    value)`` pair — and ``finalize`` folds the top-level fragments into a
    nested Python dict, then dumps it with PyYAML.

    PyYAML is an optional dependency (extra ``[yaml]``); importing this
    module never requires it. Calling ``finalize`` without it raises a
    clear, actionable error.
    """

    mode = "yaml"

    def rendered_item(
        self,
        node: Any,
        item: Any,
        runtime_attrs: dict[str, Any],
        *,
        tag: str,
        **_opts: Any,
    ) -> dict[str, Any]:
        """Turn one node into a ``(tag, value)`` structure fragment.

        ``runtime_attrs`` is already pointer-resolved and keyword-
        normalized by the walk. ``item`` is the list of child fragments
        (when the node value is a Bag) or the resolved leaf value. The
        value is the node's attributes merged with its children; a
        childless, attribute-less node maps to ``None``.
        """
        value: dict[str, Any] = {}
        for name, attr_value in runtime_attrs.items():
            if attr_value is None:
                continue
            value[name] = self._to_yaml_value(attr_value)
        if isinstance(item, list):
            for child in item:
                self._merge(value, child["tag"], child["value"])
        elif item is not None:
            return {"tag": tag, "value": self._to_yaml_value(item)}
        return {"tag": tag, "value": value or None}

    def finalize(self, result: Any, target: Any, **_opts: Any) -> Any:
        """Fold the top-level fragments into a nested dict, dump to YAML.

        ``result`` is the list of top-level ``(tag, value)`` fragments.
        Duplicate top-level tags merge into one mapping.
        """
        if _pyyaml is None:
            raise RuntimeError(
                "YAML rendering requires PyYAML. "
                "Install it with: pip install genro-builders[yaml]"
            ) from _PYYAML_IMPORT_ERROR
        document: dict[str, Any] = {}
        for fragment in result:
            self._merge(document, fragment["tag"], fragment["value"])
        text = _pyyaml.dump(document, default_flow_style=False, allow_unicode=True)
        return super().finalize(text, target)

    def _merge(self, parent: dict[str, Any], tag: str, value: Any) -> None:
        """Add ``tag: value`` to ``parent``, merging into a duplicate key."""
        if tag in parent and isinstance(parent[tag], dict) and isinstance(value, dict):
            parent[tag].update(value)
        else:
            parent[tag] = value

    def _to_yaml_value(self, value: Any) -> Any:
        """Map a resolved attribute to a YAML-friendly value.

        Comma-separated strings become lists; everything else passes
        through unchanged.
        """
        if isinstance(value, str) and "," in value:
            return [v.strip() for v in value.split(",") if v.strip()]
        return value
