# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""YamlRendererBase — render a built Bag into a YAML string.

Uses the standard top-down walk with a dict as parent. Each handler
receives the parent dict and adds its contribution. Children recurse
into the same or a nested dict.

Tag-specific handlers use @renderer, same as other renderers.
Subclasses override _render_attr_entry() for tool-specific attribute
rendering (e.g. nested attrs for Traefik, flat for Compose).

Example:
    >>> class TraefikRenderer(YamlRendererBase):
    ...     @renderer()
    ...     def router(self, node, parent):
    ...         # custom key nesting
    ...         parent["http.routers"] = node.runtime_value
"""
from __future__ import annotations

import copy
from typing import Any

import yaml
from genro_bag import Bag

from genro_builders.renderer import CTX_KEYS, BagRendererBase


class YamlRendererBase(BagRendererBase):
    """YAML renderer — top-down walk with dict as parent.

    The parent is a dict. Each node adds its tag as key with resolved
    attributes and children as value. Duplicate keys are merged.
    """

    def __init__(self, builder: Any = None) -> None:
        if builder is not None:
            super().__init__(builder)
        else:
            self.builder = None
            self._render_handlers = dict(type(self)._class_render_handlers)
            self._render_kwargs = dict(type(self)._class_render_kwargs)

    def render(self, built_bag: Bag, output: Any = None) -> str:
        """Render built Bag to YAML string."""
        root = next(iter(built_bag), None)
        if root is None:
            return ""
        root_value = root.value if hasattr(root, "value") else root
        if not isinstance(root_value, Bag):
            return ""
        result: dict[str, Any] = {}
        self._walk_render(root_value, parent=result)
        return yaml.dump(result, default_flow_style=False, allow_unicode=True)

    def _dispatch_render(self, node: Any, parent: Any) -> None:
        """Render a single node into the parent dict."""
        tag = node.node_tag or node.label

        handler = self._render_handlers.get(tag)
        if handler:
            handler(self, node, self._resolve_ctx(node), parent)
        else:
            self._render_default(node, tag, parent)

        # Children: recurse into a nested dict that becomes the value
        node_value = node.get_value(static=True)
        if isinstance(node_value, Bag):
            # Get or create the dict for this tag's content
            content = parent.get(tag)
            if isinstance(content, dict):
                self._walk_render(node_value, parent=content)
            else:
                child_dict: dict[str, Any] = {}
                self._walk_render(node_value, parent=child_dict)
                if child_dict:
                    if isinstance(content, dict):
                        content.update(child_dict)
                    else:
                        parent[tag] = child_dict

    def _walk_render(self, bag: Any, parent: Any = None) -> Any:
        """Walk bag nodes into the parent dict."""
        if parent is None:
            parent = {}
        for node in bag:
            self._dispatch_render(node, parent)
        return parent

    def _resolve_ctx(self, node: Any) -> dict[str, Any]:
        """Resolve node attributes into a flat dict via _render_attr_entry."""
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

        return result

    def _render_default(self, node: Any, tag: str,
                        parent: dict[str, Any]) -> None:
        """Default: tag as YAML key, resolved attrs as value."""
        content = self._resolve_ctx(node)
        if tag in parent and isinstance(parent[tag], dict) and isinstance(content, dict):
            parent[tag].update(content)
        else:
            parent[tag] = content if content else None

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
