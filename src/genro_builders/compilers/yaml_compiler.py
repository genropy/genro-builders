# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""YamlRendererBase — render a built Bag into a YAML string.

3-phase pipeline:
1. Walk + resolve: evaluate_on_node on each node
2. Produce dict: merge duplicate keys (e.g. two entryPoints nodes)
3. Serialize: yaml.dump(dict) → str

Tag-specific handlers use @renderer, same as other renderers.
Subclasses override _render_attr_entry() for tool-specific attribute
rendering (e.g. nested attrs for Traefik, flat for Compose).

Example:
    >>> class TraefikRenderer(YamlRendererBase):
    ...     def _render_attr_entry(self, attr_name, value, result):
    ...         # nested keys: rule → http.routers.name.rule
    ...         result[attr_name] = value
"""
from __future__ import annotations

import copy
from typing import Any

import yaml
from genro_bag import Bag

from genro_builders.renderer import CTX_KEYS, BagRendererBase


class YamlRendererBase(BagRendererBase):
    """YAML renderer — walk, merge to dict, serialize to string.

    Override render() is intentional here: YAML needs a dict merge phase
    between walk and output. The walk uses evaluate_on_node for resolution.
    """

    def __init__(self, builder: Any = None) -> None:
        if builder is not None:
            super().__init__(builder)
        else:
            self.builder = None
            self._render_handlers = dict(type(self)._class_render_handlers)
            self._render_kwargs = dict(type(self)._class_render_kwargs)

    def render(self, built_bag: Bag, output: Any = None) -> str:
        """Render built Bag to YAML string.

        Phase 1+2: walk + resolve → dict with merged keys.
        Phase 3: yaml.dump → str.
        """
        root = next(iter(built_bag), None)
        if root is None:
            return ""
        root_value = root.value if hasattr(root, "value") else root
        if not isinstance(root_value, Bag):
            return ""
        result = self._walk_to_dict(root_value)
        return yaml.dump(result, default_flow_style=False, allow_unicode=True)

    def _walk_to_dict(self, bag: Bag) -> dict[str, Any]:
        """Walk a Bag, resolve nodes, merge into dict."""
        result: dict[str, Any] = {}
        for node in bag:
            tag = node.node_tag or node.label

            handler = self._render_handlers.get(tag)
            if handler:
                handler(self, node, result)
            else:
                self._render_default(node, tag, result)
        return result

    def _render_default(self, node: Any, tag: str,
                        result: dict[str, Any]) -> None:
        """Default: tag as YAML key, resolved attrs + children as value."""
        content = self._render_node_attrs(node)
        if tag in result and isinstance(result[tag], dict) and isinstance(content, dict):
            result[tag].update(content)
        else:
            result[tag] = content

    def _render_node_attrs(self, node: Any) -> dict[str, Any]:
        """Render resolved attributes and children into a dict."""
        result: dict[str, Any] = {}

        if hasattr(node, "evaluate_on_node") and self.builder is not None:
            resolved = node.evaluate_on_node(self.builder.data)
            attrs = resolved["attrs"]
        else:
            attrs = dict(node.attr)

        for attr_name, attr_value in attrs.items():
            if attr_name.startswith("_") or attr_name in CTX_KEYS:
                continue
            if attr_value is None:
                continue
            if isinstance(attr_value, (dict, list)):
                attr_value = copy.deepcopy(attr_value)
            self._render_attr_entry(attr_name, attr_value, result)

        node_value = node.get_value(static=True)
        if isinstance(node_value, Bag):
            children = self._walk_to_dict(node_value)
            result.update(children)

        return result

    def _render_attr_entry(self, attr_name: str, value: Any,
                           result: dict[str, Any]) -> None:
        """Add one attribute to the result dict.

        Override in subclasses for tool-specific rendering
        (e.g. nested keys for Traefik, flat for Compose).
        """
        result[attr_name] = self._to_yaml_value(value)

    def _to_yaml_value(self, value: Any) -> Any:
        """Convert Python value to YAML-friendly value.

        Comma-separated strings are split into lists.
        """
        if isinstance(value, list):
            return value
        if isinstance(value, str) and "," in value:
            return [v.strip() for v in value.split(",") if v.strip()]
        return value
