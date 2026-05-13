# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CssRenderer — renderer for the CSS dialect (level 1).

Walks a built bag and produces CSS source. CSS is not XML, so this
renderer does not go through ``render_xml``: it emits the
``selector-list { prop: value; ... }`` syntax directly.

Inputs the renderer recognises:

- ``stylesheet`` nodes (optional top-level container): the renderer
  iterates their child rules.
- ``rule`` nodes (also accepted at the bag root, for fragments): the
  selector-list comes from the ``selector`` children; the property
  declarations come from ``node.attr`` (underscores converted to
  hyphens); any ``cssvar`` children are emitted as ``--name: value;``
  lines after the regular properties.
- ``selector`` nodes (children of a rule): built from kwargs.
  Structured kwargs (``tag``, ``id``, ``_class``, ``classes``,
  ``attr``) are validated with strict regexes; the ``raw`` kwarg is
  an opaque suffix that the renderer joins to the structured part
  with a leading space (for combinators and anything not covered by
  the structured form).
- ``cssvar`` nodes (children of a rule): name from ``node.value``,
  value from the ``value`` kwarg.

Comment support: any element accepts an optional ``comment="..."``
kwarg. The renderer extracts it from the attribute set and emits a
CSS comment ``/* text */``:

- ``len(comment) <= COMMENT_INLINE_MAX_LEN`` (60) -> inline, appended
  to the last property line (rule) or to the declaration (cssvar).
- otherwise -> block comment on its own line above the element.

Validation is eager: invalid ``tag`` / ``id`` / ``_class`` / ``classes``
/ ``attr`` values raise ``ValueError`` at render time with a clear
message.
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
    # Dispatch
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
                    self._render_top_node(child, lines, pretty=pretty, indent=indent, depth=depth)
            return
        if tag == "rule":
            self._render_rule(node, lines, pretty=pretty, indent=indent, depth=depth)

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def _render_rule(
        self,
        node: Any,
        lines: list[str],
        *,
        pretty: bool,
        indent: str,
        depth: int,
    ) -> None:
        attrs = dict(node.attr)
        comment = attrs.pop("comment", None)
        selectors = self._collect_selectors(node)
        if not selectors:
            raise ValueError("rule has no selector children; add at least one .selector(...)")
        selector_list = ", ".join(selectors)

        outer = indent * depth if pretty else ""
        inner = indent * (depth + 1) if pretty else ""

        if comment is not None and len(str(comment)) > COMMENT_INLINE_MAX_LEN:
            lines.append(f"{outer}/* {comment} */")
            inline_comment: str | None = None
        else:
            inline_comment = str(comment) if comment is not None else None

        property_lines = self._format_properties(attrs)
        cssvar_lines = self._format_cssvars(node)
        nested_blocks = self._collect_nested_rules(node)

        body = property_lines + cssvar_lines
        if inline_comment is not None and body:
            body[-1] = f"{body[-1]} /* {inline_comment} */"
        elif inline_comment is not None and not body and not nested_blocks:
            body = [f"/* {inline_comment} */"]

        if pretty:
            lines.append(f"{outer}{selector_list} {{")
            for entry in body:
                lines.append(f"{inner}{entry}")
            for nested in nested_blocks:
                self._render_rule(
                    nested, lines, pretty=pretty, indent=indent, depth=depth + 1,
                )
            lines.append(f"{outer}}}")
        else:
            body_text = " ".join(body)
            if nested_blocks:
                nested_lines: list[str] = []
                for nested in nested_blocks:
                    self._render_rule(
                        nested, nested_lines, pretty=False, indent=indent, depth=0,
                    )
                nested_text = " ".join(nested_lines)
                combined = " ".join(part for part in (body_text, nested_text) if part)
                lines.append(f"{selector_list} {{ {combined} }}")
            else:
                lines.append(f"{selector_list} {{ {body_text} }}")

    def _collect_nested_rules(self, rule_node: Any) -> list[Any]:
        """Return the child ``rule`` nodes of ``rule_node`` in document order."""
        result: list[Any] = []
        value = rule_node.value
        if not isinstance(value, Bag):
            return result
        for child in value:
            if (child.node_tag or child.label) == "rule":
                result.append(child)
        return result

    def _format_properties(self, attrs: dict[str, Any]) -> list[str]:
        """One CSS declaration per property kwarg."""
        result: list[str] = []
        for raw_name, value in attrs.items():
            if raw_name.startswith("_"):
                continue
            css_name = raw_name.replace("_", "-")
            result.append(f"{css_name}: {value};")
        return result

    # ------------------------------------------------------------------
    # Selectors
    # ------------------------------------------------------------------

    def _collect_selectors(self, rule_node: Any) -> list[str]:
        """Return the rendered string for each selector child of a rule."""
        result: list[str] = []
        value = rule_node.value
        if not isinstance(value, Bag):
            return result
        for child in value:
            if (child.node_tag or child.label) != "selector":
                continue
            result.append(self._format_selector(child))
        return result

    def _format_selector(self, node: Any) -> str:
        """Compose a single selector string from a ``selector`` node."""
        attrs = dict(node.attr)
        attrs.pop("comment", None)  # silently ignored on selector for now

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
    # CSS variables
    # ------------------------------------------------------------------

    def _format_cssvars(self, rule_node: Any) -> list[str]:
        """Return one CSS declaration per ``cssvar`` child of ``rule_node``."""
        result: list[str] = []
        value = rule_node.value
        if not isinstance(value, Bag):
            return result
        for child in value:
            if (child.node_tag or child.label) != "cssvar":
                continue
            result.extend(self._format_cssvar(child))
        return result

    def _format_cssvar(self, node: Any) -> list[str]:
        """One (or two, with block comment) lines for a cssvar."""
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
