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
  body comes from the rule(s), cssvar(s) and nested selector(s)
  of the node.
- ``selector_list`` nodes: hold N ``selector`` children whose
  compounds form a comma-separated selector-list; the body comes
  from the same set of child element types.

Rules grouping: a selector may carry multiple ``rule`` children.
Each rule may declare optional ``media`` and ``supports`` kwargs.
The renderer groups rules by ``(media, supports)``:

- the group ``(None, None)`` is emitted as the base block;
- each non-base group is emitted as a nested ``@media`` /
  ``@supports`` block re-using the parent selector inside.

Selector composition: structured kwargs (``tag``, ``id``,
``_class``, ``classes``, ``attr``) are validated with strict
regexes; ``raw`` is an opaque suffix joined with a leading space.

Comment support: any element accepts ``comment="..."``. The
renderer emits ``/* ... */`` inline when the text fits in
``COMMENT_INLINE_MAX_LEN`` (60), otherwise as a block above the
element.
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
        self._render_top_sequence(
            list(built), lines, pretty=pretty, indent=indent, depth=0,
        )
        text = "\n".join(lines) + ("\n" if lines else "") if pretty else "".join(lines)
        return self._write_or_return(text, render_target)

    # ------------------------------------------------------------------
    # Top-level dispatch
    # ------------------------------------------------------------------

    def _render_top_sequence(
        self,
        nodes: list[Any],
        lines: list[str],
        *,
        pretty: bool,
        indent: str,
        depth: int,
    ) -> None:
        """Render a sequence of top-level nodes.

        Top-level ``cssvar`` children (direct children of the bag root
        or of a ``stylesheet``) are gathered into a single implicit
        ``:root { ... }`` block. Consecutive cssvars share the same
        block; a non-cssvar node flushes the buffer first.
        """
        cssvar_buffer: list[Any] = []

        def flush() -> None:
            if not cssvar_buffer:
                return
            self._emit_root_cssvar_block(
                cssvar_buffer, lines, pretty=pretty, indent=indent, depth=depth,
            )
            cssvar_buffer.clear()

        for node in nodes:
            tag = node.node_tag or node.label
            if tag == "cssvar":
                cssvar_buffer.append(node)
                continue
            flush()
            self._render_top_node(node, lines, pretty=pretty, indent=indent, depth=depth)
        flush()

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
                self._render_top_sequence(
                    list(value), lines, pretty=pretty, indent=indent, depth=depth,
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

    def _emit_root_cssvar_block(
        self,
        cssvars: list[Any],
        lines: list[str],
        *,
        pretty: bool,
        indent: str,
        depth: int,
    ) -> None:
        """Emit a list of ``cssvar`` nodes as a single ``:root { ... }`` block."""
        body: list[str] = []
        for var_node in cssvars:
            body.extend(self._format_cssvar(var_node))
        if not body:
            return
        outer = indent * depth if pretty else ""
        inner = indent * (depth + 1) if pretty else ""
        if pretty:
            lines.append(f"{outer}:root {{")
            for entry in body:
                lines.append(f"{inner}{entry}")
            lines.append(f"{outer}}}")
        else:
            lines.append(":root { " + " ".join(body) + " }")

    def _render_selector_list(
        self,
        node: Any,
        lines: list[str],
        *,
        pretty: bool,
        indent: str,
        depth: int,
    ) -> None:
        selectors: list[str] = []
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
        Body comes from the rule(s), cssvar(s) and nested selector(s)
        of ``node``. Rules are grouped by ``(media, supports)``;
        the base group is inlined, the others are emitted as
        nested ``@media`` / ``@supports`` blocks.
        """
        selector_list = ", ".join(selector_strings)
        outer = indent * depth if pretty else ""
        inner = indent * (depth + 1) if pretty else ""

        block_comment = self._block_comment(node)
        rule_groups = self._group_rules(node)
        base_properties = rule_groups.pop((None, None), [])
        cssvar_lines = self._format_cssvars(node)
        nested_selectors = (
            [] if consume_selectors_as_list
            else self._find_children(node, "selector")
        )

        body = base_properties + cssvar_lines
        if block_comment.position == "block" and block_comment.text:
            lines.append(f"{outer}/* {block_comment.text} */")
        inline_comment = block_comment.text if block_comment.position == "inline" else None
        if inline_comment is not None and body:
            body[-1] = f"{body[-1]} /* {inline_comment} */"
        elif (
            inline_comment is not None
            and not body
            and not nested_selectors
            and not rule_groups
        ):
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
            for (media, supports), properties in rule_groups.items():
                self._emit_at_group(
                    media, supports, selector_strings, properties, lines,
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
            for (media, supports), properties in rule_groups.items():
                _flat = []
                self._emit_at_group(
                    media, supports, selector_strings, properties, _flat,
                    pretty=False, indent=indent, depth=0,
                )
                extras.append(" ".join(_flat))
            body_text = " ".join(body)
            combined = " ".join(part for part in (body_text, *extras) if part)
            lines.append(f"{selector_list} {{ {combined} }}")

    # ------------------------------------------------------------------
    # Rule grouping by (media, supports)
    # ------------------------------------------------------------------

    def _group_rules(
        self, node: Any,
    ) -> dict[tuple[str | None, str | None], list[str]]:
        """Group rule children by (media, supports). Preserves order.

        The result is a dict keyed by the (media, supports) tuple,
        with values being the merged list of CSS declaration lines
        (in the order rules were added). The (None, None) key is
        the base block.
        """
        groups: dict[tuple[str | None, str | None], list[str]] = {}
        for rule_node in self._find_children(node, "rule"):
            attrs = dict(rule_node.attr)
            attrs.pop("comment", None)
            media = attrs.pop("media", None)
            supports = attrs.pop("supports", None)
            key = (media, supports)
            properties = self._format_properties(attrs)
            if key not in groups:
                groups[key] = []
            groups[key].extend(properties)
        return groups

    def _emit_at_group(
        self,
        media: str | None,
        supports: str | None,
        parent_selectors: list[str],
        properties: list[str],
        lines: list[str],
        *,
        pretty: bool,
        indent: str,
        depth: int,
    ) -> None:
        """Emit a @media and/or @supports block re-using the parent selector.

        When both ``media`` and ``supports`` are present, the
        ``@supports`` block wraps the ``@media`` block.
        """
        parent_selector_list = ", ".join(parent_selectors)

        if pretty:
            current_depth = depth
            outer = indent * current_depth

            if supports is not None:
                lines.append(f"{outer}@supports {supports} {{")
                current_depth += 1
                outer = indent * current_depth
            if media is not None:
                lines.append(f"{outer}@media {media} {{")
                current_depth += 1
                outer = indent * current_depth

            lines.append(f"{outer}{parent_selector_list} {{")
            inner = indent * (current_depth + 1)
            for entry in properties:
                lines.append(f"{inner}{entry}")
            lines.append(f"{outer}}}")

            if media is not None:
                current_depth -= 1
                lines.append(f"{indent * current_depth}}}")
            if supports is not None:
                current_depth -= 1
                lines.append(f"{indent * current_depth}}}")
        else:
            inner_props = " ".join(properties)
            payload = f"{parent_selector_list} {{ {inner_props} }}"
            if media is not None:
                payload = f"@media {media} {{ {payload} }}"
            if supports is not None:
                payload = f"@supports {supports} {{ {payload} }}"
            lines.append(payload)

    # ------------------------------------------------------------------
    # Properties / cssvars
    # ------------------------------------------------------------------

    def _format_properties(self, attrs: dict[str, Any]) -> list[str]:
        """One CSS declaration per property kwarg.

        Underscores in the Python kwarg name are translated to hyphens
        in the CSS property name. A leading underscore therefore yields
        a leading hyphen, which is exactly how vendor prefixes are
        spelled in CSS (``_webkit_user_select`` → ``-webkit-user-select``).
        """
        result: list[str] = []
        for raw_name, value in attrs.items():
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
