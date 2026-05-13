# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CssRenderer — renderer for the CSS dialect (level 1).

Walks a built bag and produces CSS source. CSS is not XML, so this
renderer does not go through ``render_xml``: it emits the
``selector-list { prop: value; ... }`` syntax directly.

Top-level dispatch:

- ``stylesheet`` nodes (optional top-level container): the renderer
  iterates their children.
- ``selector`` nodes (also accepted at the bag root, for fragments):
  the selector's own compound forms a one-entry selector-list; the
  body comes from the ``rule`` / ``media`` / ``supports`` / ``cssvar``
  / nested ``selector`` children.
- ``selector_list`` nodes: hold N ``selector`` children whose
  compounds form a comma-separated selector-list; the body comes
  from the same set of child element types.

Selector composition: structured kwargs (``tag``, ``id``, ``_class``,
``classes``, ``attr``) are validated with strict regexes; the
``raw`` kwarg is an opaque suffix that the renderer joins to the
structured part with a leading space (for combinators).

Comment support: any element accepts an optional ``comment="..."``
kwarg. The renderer extracts it from the attribute set and emits a
CSS comment ``/* text */``:

- ``len(comment) <= COMMENT_INLINE_MAX_LEN`` (60) -> inline, appended
  to the last property line.
- otherwise -> block comment on its own line above the element.
"""

from __future__ import annotations

import re
from typing import Any

from genro_bag import Bag

from ...renderer import RendererBase

COMMENT_INLINE_MAX_LEN = 60

_RE_TAG = re.compile(r"^[a-zA-Z][\w-]*$")
_RE_ID = re.compile(r"^[a-zA-Z_-][\w-]*$")
_RE_CLASS = re.compile(r"^[a-zA-Z_-][\w-]*(:{1,2}[\w-]+)*$")
_RE_ATTR_NAME = re.compile(r"^[a-zA-Z_-][\w-]*$")


class CssRenderer(RendererBase):
    """Renderer for the CSS dialect (one mode: ``render_css``)."""

    def render_css(
        self,
        built: Bag,
        render_target: Any = None,
        *,
        pretty: bool = True,
        indent: str = "  ",
    ) -> str | None:
        """Serialize ``built`` as CSS source. See module docstring."""
        lines: list[str] = []
        for node in built:
            self._render_top_node(node, lines, pretty=pretty, indent=indent, depth=0)
        text = "\n".join(lines) + ("\n" if lines else "") if pretty else "".join(lines)
        return self._write_or_return(text, render_target)

    # ------------------------------------------------------------------
    # Top-level dispatch
    # ------------------------------------------------------------------

    def _render_top_node(
        self,
        node: Any,
        lines: list[str],
        *,
        pretty: bool,
        indent: str,
        depth: int,
    ) -> None:
        tag = node.node_tag or node.label
        if tag == "stylesheet":
            value = node.value
            if isinstance(value, Bag):
                for child in value:
                    self._render_top_node(
                        child, lines, pretty=pretty, indent=indent, depth=depth,
                    )
            return
        if tag == "selector":
            self._render_block(
                [self._format_selector(node)], node, lines,
                pretty=pretty, indent=indent, depth=depth,
            )
            return
        if tag == "selector_list":
            self._render_selector_list(
                node, lines, pretty=pretty, indent=indent, depth=depth,
            )

    def _render_selector_list(
        self,
        node: Any,
        lines: list[str],
        *,
        pretty: bool,
        indent: str,
        depth: int,
    ) -> None:
        selectors = []
        value = node.value
        if isinstance(value, Bag):
            for child in value:
                if (child.node_tag or child.label) == "selector":
                    selectors.append(self._format_selector(child))
        if not selectors:
            raise ValueError(
                "selector_list has no selector children; add at least one .selector(...)",
            )
        self._render_block(
            selectors, node, lines, pretty=pretty, indent=indent, depth=depth,
            consume_selectors_as_list=True,
        )

    # ------------------------------------------------------------------
    # Block emission (selector or selector_list)
    # ------------------------------------------------------------------

    def _render_block(
        self,
        selector_strings: list[str],
        node: Any,
        lines: list[str],
        *,
        pretty: bool,
        indent: str,
        depth: int,
        consume_selectors_as_list: bool = False,
    ) -> None:
        """Emit a ``selectors { body }`` block.

        ``selector_strings`` is the comma-separated selector-list
        (one entry for a plain selector, N for a selector_list).
        Body comes from ``rule``/``media``/``supports``/``cssvar``/
        nested ``selector`` children of ``node``.

        When ``consume_selectors_as_list`` is True (selector_list
        case), ``selector`` children are NOT treated as nested
        blocks — they have already been used to build the
        comma-separated list.
        """
        selector_list = ", ".join(selector_strings)
        outer = indent * depth if pretty else ""
        inner = indent * (depth + 1) if pretty else ""

        block_comment = self._block_comment(node)

        rule_node = self._find_child(node, "rule")
        property_lines = self._format_properties_from_rule(rule_node)
        cssvar_lines = self._format_cssvars(node)
        nested_selectors = (
            [] if consume_selectors_as_list
            else self._find_children(node, "selector")
        )
        media_nodes = self._find_children(node, "media")
        supports_nodes = self._find_children(node, "supports")

        body = property_lines + cssvar_lines

        if block_comment.position == "block" and block_comment.text:
            lines.append(f"{outer}/* {block_comment.text} */")
        inline_comment = block_comment.text if block_comment.position == "inline" else None

        if inline_comment is not None and body:
            body[-1] = f"{body[-1]} /* {inline_comment} */"
        elif inline_comment is not None and not body and not nested_selectors and not media_nodes and not supports_nodes:
            body = [f"/* {inline_comment} */"]

        if pretty:
            lines.append(f"{outer}{selector_list} {{")
            for entry in body:
                lines.append(f"{inner}{entry}")
            for nested in nested_selectors:
                self._render_block(
                    [self._format_selector(nested)], nested, lines,
                    pretty=pretty, indent=indent, depth=depth + 1,
                )
            for media in media_nodes:
                self._render_at_block(
                    "media", media, selector_strings, lines,
                    pretty=pretty, indent=indent, depth=depth + 1,
                )
            for sup in supports_nodes:
                self._render_at_block(
                    "supports", sup, selector_strings, lines,
                    pretty=pretty, indent=indent, depth=depth + 1,
                )
            lines.append(f"{outer}}}")
        else:
            extras: list[str] = []
            for nested in nested_selectors:
                _flat: list[str] = []
                self._render_block(
                    [self._format_selector(nested)], nested, _flat,
                    pretty=False, indent=indent, depth=0,
                )
                extras.append(" ".join(_flat))
            for media in media_nodes:
                _flat = []
                self._render_at_block(
                    "media", media, selector_strings, _flat,
                    pretty=False, indent=indent, depth=0,
                )
                extras.append(" ".join(_flat))
            for sup in supports_nodes:
                _flat = []
                self._render_at_block(
                    "supports", sup, selector_strings, _flat,
                    pretty=False, indent=indent, depth=0,
                )
                extras.append(" ".join(_flat))
            body_text = " ".join(body)
            combined = " ".join(part for part in (body_text, *extras) if part)
            lines.append(f"{selector_list} {{ {combined} }}")

    # ------------------------------------------------------------------
    # @media / @supports
    # ------------------------------------------------------------------

    def _render_at_block(
        self,
        at_name: str,
        node: Any,
        parent_selectors: list[str],
        lines: list[str],
        *,
        pretty: bool,
        indent: str,
        depth: int,
    ) -> None:
        """Emit a @media or @supports block inside a selector block.

        Property kwargs of the at-block apply to the parent
        selector-list inside the @at(condition) { ... }.
        """
        attrs = dict(node.attr)
        condition = attrs.pop("condition", None)
        if not condition:
            raise ValueError(f"@{at_name} requires a condition kwarg")
        attrs.pop("comment", None)

        property_lines = self._format_properties(attrs)
        nested_selectors = self._find_children(node, "selector")

        parent_selector_list = ", ".join(parent_selectors)
        outer = indent * depth if pretty else ""
        inner = indent * (depth + 1) if pretty else ""
        inner2 = indent * (depth + 2) if pretty else ""

        if pretty:
            lines.append(f"{outer}@{at_name} {condition} {{")
            if property_lines:
                lines.append(f"{inner}{parent_selector_list} {{")
                for entry in property_lines:
                    lines.append(f"{inner2}{entry}")
                lines.append(f"{inner}}}")
            for nested in nested_selectors:
                self._render_block(
                    [self._format_selector(nested)], nested, lines,
                    pretty=pretty, indent=indent, depth=depth + 1,
                )
            lines.append(f"{outer}}}")
        else:
            body_parts: list[str] = []
            if property_lines:
                inner_props = " ".join(property_lines)
                body_parts.append(f"{parent_selector_list} {{ {inner_props} }}")
            for nested in nested_selectors:
                _flat: list[str] = []
                self._render_block(
                    [self._format_selector(nested)], nested, _flat,
                    pretty=False, indent=indent, depth=0,
                )
                body_parts.append(" ".join(_flat))
            inner_text = " ".join(body_parts)
            lines.append(f"@{at_name} {condition} {{ {inner_text} }}")

    # ------------------------------------------------------------------
    # Properties / cssvars
    # ------------------------------------------------------------------

    def _format_properties_from_rule(self, rule_node: Any) -> list[str]:
        if rule_node is None:
            return []
        attrs = dict(rule_node.attr)
        attrs.pop("comment", None)
        return self._format_properties(attrs)

    def _format_properties(self, attrs: dict[str, Any]) -> list[str]:
        """One CSS declaration per property kwarg."""
        result: list[str] = []
        for raw_name, value in attrs.items():
            if raw_name.startswith("_"):
                continue
            if raw_name == "condition":
                continue
            css_name = raw_name.replace("_", "-")
            result.append(f"{css_name}: {value};")
        return result

    def _format_cssvars(self, node: Any) -> list[str]:
        """One declaration per ``cssvar`` child."""
        result: list[str] = []
        for child in self._find_children(node, "cssvar"):
            result.extend(self._format_cssvar(child))
        return result

    def _format_cssvar(self, node: Any) -> list[str]:
        name = node.value if node.value is not None else ""
        attrs = dict(node.attr)
        comment = attrs.pop("comment", None)
        var_value = attrs.pop("value", "")
        declaration = f"--{name}: {var_value};"
        if comment is None:
            return [declaration]
        text = str(comment)
        if len(text) <= COMMENT_INLINE_MAX_LEN:
            return [f"{declaration} /* {text} */"]
        return [f"/* {text} */", declaration]

    # ------------------------------------------------------------------
    # Selector compounding
    # ------------------------------------------------------------------

    def _format_selector(self, node: Any) -> str:
        attrs = dict(node.attr)
        attrs.pop("comment", None)

        tag = attrs.pop("tag", None)
        sel_id = attrs.pop("id", None)
        single_class = attrs.pop("_class", None)
        many_classes = attrs.pop("classes", None)
        attr_map = attrs.pop("attr", None)
        raw = attrs.pop("raw", None)

        if single_class is not None and many_classes is not None:
            raise ValueError(
                "selector: pass either _class (single) or classes (list), not both",
            )

        parts: list[str] = []
        if tag is not None:
            if not isinstance(tag, str) or not _RE_TAG.match(tag):
                raise ValueError(
                    f"selector tag {tag!r}: must match [a-zA-Z][\\w-]*",
                )
            parts.append(tag)
        if sel_id is not None:
            if not isinstance(sel_id, str) or not _RE_ID.match(sel_id):
                raise ValueError(
                    f"selector id {sel_id!r}: must match [a-zA-Z_-][\\w-]*",
                )
            parts.append(f"#{sel_id}")
        class_list: list[str] = []
        if single_class is not None:
            if not isinstance(single_class, str):
                raise ValueError(
                    f"selector _class {single_class!r}: must be a string; "
                    "use classes=[...] for multiple",
                )
            class_list = [single_class]
        elif many_classes is not None:
            if not isinstance(many_classes, (list, tuple)):
                raise ValueError(
                    f"selector classes {many_classes!r}: must be a list",
                )
            class_list = list(many_classes)
        for item in class_list:
            if not isinstance(item, str) or not _RE_CLASS.match(item):
                raise ValueError(
                    f"selector class {item!r}: must match "
                    "[a-zA-Z_-][\\w-]*(:{1,2}[\\w-]+)* "
                    "(no spaces, no dots, no combinators)",
                )
            parts.append(f".{item}")
        if attr_map is not None:
            if not isinstance(attr_map, dict):
                raise ValueError(
                    f"selector attr {attr_map!r}: must be a dict",
                )
            for name, value in attr_map.items():
                if not isinstance(name, str) or not _RE_ATTR_NAME.match(name):
                    raise ValueError(
                        f"selector attr name {name!r}: must match "
                        "[a-zA-Z_-][\\w-]*",
                    )
                if value is None:
                    parts.append(f"[{name}]")
                else:
                    parts.append(f'[{name}="{value}"]')

        compound = "".join(parts)
        if raw is not None:
            raw_str = str(raw)
            if compound:
                return f"{compound} {raw_str}"
            return raw_str
        if not compound:
            raise ValueError(
                "selector: at least one of tag/id/_class/classes/attr/raw "
                "must be provided",
            )
        return compound

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def _block_comment(self, node: Any) -> _CommentSpec:
        text = node.attr.get("comment")
        if text is None:
            return _CommentSpec(text=None, position="inline")
        s = str(text)
        if len(s) <= COMMENT_INLINE_MAX_LEN:
            return _CommentSpec(text=s, position="inline")
        return _CommentSpec(text=s, position="block")

    # ------------------------------------------------------------------
    # Bag helpers
    # ------------------------------------------------------------------

    def _find_child(self, node: Any, tag: str) -> Any:
        value = node.value
        if not isinstance(value, Bag):
            return None
        for child in value:
            if (child.node_tag or child.label) == tag:
                return child
        return None

    def _find_children(self, node: Any, tag: str) -> list[Any]:
        value = node.value
        if not isinstance(value, Bag):
            return []
        return [
            child for child in value
            if (child.node_tag or child.label) == tag
        ]


class _CommentSpec:
    """Tiny holder for comment text + inline/block position."""

    __slots__ = ("text", "position")

    def __init__(self, *, text: str | None, position: str) -> None:
        self.text = text
        self.position = position
