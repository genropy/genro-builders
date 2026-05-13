# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlRenderer — renderer for the HTML5 dialect.

Walks a built bag and produces HTML5 markup. Bound to ``HtmlBuilder``
via ``HtmlBuilder._renderer_class``. Exposed on the handler as
``handler.renderer`` (with ``handler.render(...)`` as shortcut).

Features:

- Void tag self-close: by default XHTML-style ``<img src="x"/>`` so
  the output is also XML well-formed; ``xml=False`` switches to the
  idiomatic HTML5 form ``<img src="x">``.
- Pretty-print: ``pretty=True`` produces multi-line indented output
  (2 spaces per level), text-only leaves stay on a single line.
- Keyword-collision attributes: ``_class`` → ``class``, ``_for`` →
  ``for``. Underscore-prefix attributes outside this map are dropped
  (they belong to bag internals, not to HTML).
- Three-state booleans: ``True`` / ``False`` / ``None`` attribute
  values are serialised as JS literals (``"true"``, ``"false"``,
  ``"null"``). ``None`` is currently filtered upstream by the grammar
  dispatch, so it never reaches the renderer in practice.
- CSS kwarg support (Genro-style inline styling):
  - A kwarg is treated as a CSS property if its name appears in
    ``_STYLE_ROOTS`` or starts with one of those roots followed by
    ``_`` (e.g. ``padding_top`` matches root ``padding``).
  - Sub-kwarg ``<macro>_<sub>`` feeds Genro macros:
    ``rounded_top=10`` becomes ``border-top-left-radius: 10px``
    plus the corresponding right corner. Macro names are chosen so
    they never collide with CSS roots, so the macro lookup wins
    over the root rule with no ambiguity.
  - Prefix ``style_`` is an explicit CSS escape:
    ``style_aspect_ratio="16/9"`` → ``style="aspect-ratio: 16/9"``,
    bypassing the root lookup.
  - Explicit ``style="..."`` is parsed and merged: kwarg CSS win on
    collision (the modern, specific syntax overrides the legacy
    catch-all).
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag

from ...renderer import RendererBase


_ATTR_MAP = {"_class": "class", "_for": "for"}

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "source", "track", "wbr",
})

#: Root names that classify a kwarg as a CSS property. The rule is:
#: a kwarg is CSS if its name equals a root, or starts with a root +
#: ``"_"``. Underscore→dash conversion then yields the CSS property.
_STYLE_ROOTS = frozenset({
    # Layout / box
    "width", "height", "top", "left", "right", "bottom",
    "padding", "margin", "border", "position", "display",
    "overflow", "float", "clear", "resize", "z_index",
    # Typography / color
    "color", "background", "font", "text",
    "line_height", "white_space", "vertical_align",
    # Flex / Grid
    "flex", "gap", "row_gap", "column_gap",
    "grid_template_columns",
    "align_content", "justify_content",
    "align_items", "justify_items",
    # Visibility / interaction
    "visibility", "opacity", "cursor",
})

#: Genro-style macros. Each maps to a method
#: ``_macro_<name>(value, sub_kwargs)`` that returns a dict of CSS
#: properties (kebab-case, with units already applied).
_GENRO_MACRO_NAMES = frozenset({
    "rounded", "gradient", "shadow",
    "transform", "transition", "zoom", "filter",
})


class HtmlRenderer(RendererBase):
    """Renderer for the HTML5 dialect (one mode: ``render_html``)."""

    def render_html(
        self,
        built: Bag,
        render_target: Any = None,
        *,
        xml: bool = True,
        pretty: bool = False,
    ) -> str | None:
        """Serialize ``built`` as HTML5 markup. See module docstring."""
        chunks: list[str] = []
        for node in built:
            self._render_node(node, chunks.append, xml=xml, pretty=pretty, depth=0)
        text = "".join(chunks)
        return self._write_or_return(text, render_target)

    def _render_subtree(self, node: Any, emit: Any) -> None:
        """Entry point used by host renderers when they delegate a
        subtree to this renderer (P5). Forwards to ``_render_node`` with
        HTML defaults so the caller does not need to know HTML-specific
        walk parameters."""
        self._render_node(node, emit, xml=True, pretty=False, depth=0)

    def _render_node(
        self,
        node: Any,
        emit: Any,
        *,
        xml: bool,
        pretty: bool,
        depth: int,
    ) -> None:
        # @subbuilder polymorphism (decision 2, P5): if the node carries
        # a foreign dialect on its _builder slot, hand the whole subtree
        # off to that dialect's renderer.
        node_builder = getattr(node, "_builder", None)
        if node_builder is not None and node_builder is not self.builder:
            self._render_subbuilder(node, emit, node_builder, pretty=pretty, depth=depth)
            return
        tag = node.node_tag or node.label
        attrs = self._format_attrs(node.attr)
        indent = "  " * depth if pretty else ""
        newline = "\n" if pretty else ""
        if tag in _VOID_TAGS:
            emit(f"{indent}<{tag}{attrs}/>{newline}" if xml else f"{indent}<{tag}{attrs}>{newline}")
            return
        value = node.value
        if isinstance(value, Bag):
            emit(f"{indent}<{tag}{attrs}>{newline}")
            for child in value:
                self._render_node(
                    child, emit, xml=xml, pretty=pretty, depth=depth + 1,
                )
            emit(f"{indent}</{tag}>{newline}")
        elif value is not None:
            emit(
                f"{indent}<{tag}{attrs}>"
                f"{self._escape_text(value)}"
                f"</{tag}>{newline}"
            )
        else:
            emit(f"{indent}<{tag}{attrs}></{tag}>{newline}")

    # ------------------------------------------------------------------
    # Attribute formatting (HTML + CSS kwarg fusion)
    # ------------------------------------------------------------------

    def _format_attrs(self, attrs: dict[str, Any]) -> str:
        css: dict[str, str] = {}
        # macro values + sub-kwargs gathered per macro
        macro_value: dict[str, Any] = {}
        macro_subs: dict[str, dict[str, Any]] = {}
        html_parts: list[str] = []

        for raw_name, value in attrs.items():
            # 1. Bag-internal underscore keys (e.g. ``_tag``) — skip
            #    unless they are part of the keyword-collision map.
            if raw_name.startswith("_") and raw_name not in _ATTR_MAP:
                continue

            # 2. Explicit ``style="..."`` is parsed and seeded into css;
            #    kwarg CSS will overwrite collisions later.
            if raw_name == "style":
                css.update(_parse_style_string(value))
                continue

            # 3. ``style_<prop>`` escape: literal CSS, strip prefix.
            if raw_name.startswith("style_") and raw_name != "style":
                prop = raw_name[len("style_"):].replace("_", "-")
                css[prop] = self._css_value(value)
                continue

            # 4. Top-level macro (``rounded=10``).
            if raw_name in _GENRO_MACRO_NAMES:
                macro_value[raw_name] = value
                continue

            # 5. ``<macro>_<sub>`` sub-kwarg for a Genro macro
            #    (single underscore, matching the legacy convention).
            #    Macros never collide with CSS roots by design, so the
            #    macro lookup wins over the root rule.
            if "_" in raw_name:
                head, sub = raw_name.split("_", 1)
                if head in _GENRO_MACRO_NAMES:
                    macro_subs.setdefault(head, {})[sub] = value
                    continue

            # 6. CSS root / root_xxx rule.
            if _is_style_attr(raw_name):
                prop = raw_name.replace("_", "-")
                css[prop] = self._css_value(value)
                continue

            # 7. Plain HTML attribute (with keyword-collision remap).
            name = _ATTR_MAP.get(raw_name, raw_name)
            html_parts.append(f' {name}="{self._html_attr_value(value)}"')

        # Materialise Genro macros (may write into css).
        for macro_name in _GENRO_MACRO_NAMES:
            if macro_name in macro_value or macro_name in macro_subs:
                handler_method = getattr(self, f"_macro_{macro_name}")
                handler_method(
                    macro_value.get(macro_name),
                    macro_subs.get(macro_name, {}),
                    css,
                )

        if css:
            style_text = "; ".join(f"{k}: {v}" for k, v in css.items())
            html_parts.append(f' style="{style_text}"')

        return "".join(html_parts)

    @staticmethod
    def _html_attr_value(value: Any) -> str:
        """Render a non-CSS attribute value (three-state booleans + escape)."""
        if value is True:
            return "true"
        if value is False:
            return "false"
        if value is None:
            return "null"
        return str(value).translate(_ATTR_VALUE_ESCAPE)

    @staticmethod
    def _css_value(value: Any) -> str:
        """Render a CSS property value. No unit injection: raw stringification."""
        if value is True:
            return "true"
        if value is False:
            return "false"
        if value is None:
            return "null"
        return str(value)

    # ------------------------------------------------------------------
    # Genro CSS macros
    # ------------------------------------------------------------------

    def _macro_rounded(
        self,
        value: Any,
        subs: dict[str, Any],
        css: dict[str, str],
    ) -> None:
        """``rounded=N`` → all four border-*-radius corners at N px.

        Sub-kwargs accept group aliases (``top``, ``bottom``, ``left``,
        ``right``) and per-corner names (``top_left``, ``top_right``,
        ``bottom_left``, ``bottom_right``). Sub-kwargs win on collision
        with the top-level value.
        """
        corners: dict[str, Any] = {
            "top_left": value, "top_right": value,
            "bottom_left": value, "bottom_right": value,
        } if value is not None else {}
        for sub, sub_value in subs.items():
            if sub == "top":
                corners["top_left"] = sub_value
                corners["top_right"] = sub_value
            elif sub == "bottom":
                corners["bottom_left"] = sub_value
                corners["bottom_right"] = sub_value
            elif sub == "left":
                corners["top_left"] = sub_value
                corners["bottom_left"] = sub_value
            elif sub == "right":
                corners["top_right"] = sub_value
                corners["bottom_right"] = sub_value
            elif sub in {"top_left", "top_right", "bottom_left", "bottom_right"}:
                corners[sub] = sub_value
            # unknown sub names are silently ignored
        for corner, v in corners.items():
            css[f"border-{corner.replace('_', '-')}-radius"] = _px(v)

    def _macro_transform(
        self,
        value: Any,
        subs: dict[str, Any],
        css: dict[str, str],
    ) -> None:
        """Compose ``transform: <fn>(...) <fn>(...) ...`` from sub-kwargs.

        Top-level ``transform=...`` is passed through as a raw CSS
        string. Sub-kwargs add typed functions: ``rotate=N`` →
        ``rotate(Ndeg)``, ``scale=N`` → ``scale(N)``, ``translate_x=N``
        → ``translatex(Npx)``, etc.
        """
        parts: list[str] = []
        if value is not None:
            parts.append(str(value))
        for sub, sub_value in subs.items():
            if sub == "rotate":
                parts.append(f"rotate({sub_value}deg)")
            elif sub == "scale":
                parts.append(f"scale({sub_value})")
            elif sub == "translate":
                parts.append(f"translate({sub_value})")
            elif sub == "translate_x":
                parts.append(f"translateX({_px(sub_value)})")
            elif sub == "translate_y":
                parts.append(f"translateY({_px(sub_value)})")
            elif sub == "skew_x":
                parts.append(f"skewX({sub_value}deg)")
            elif sub == "skew_y":
                parts.append(f"skewY({sub_value}deg)")
            else:
                parts.append(f"{sub.replace('_', '-')}({sub_value})")
        if parts:
            css["transform"] = " ".join(parts)

    def _macro_filter(
        self,
        value: Any,
        subs: dict[str, Any],
        css: dict[str, str],
    ) -> None:
        """Compose ``filter: <fn>(...)`` from sub-kwargs."""
        parts: list[str] = []
        if value is not None:
            parts.append(str(value))
        for sub, sub_value in subs.items():
            if sub == "rotate":
                parts.append(f"hue-rotate({sub_value}deg)")
            elif sub == "blur":
                parts.append(f"blur({_px(sub_value)})")
            elif sub in {"invert", "contrast", "brightness",
                         "saturate", "grayscale", "sepia", "opacity"}:
                parts.append(f"{sub}({sub_value})")
            elif sub == "drop_shadow":
                parts.append(f"drop-shadow({sub_value})")
            else:
                parts.append(f"{sub.replace('_', '-')}({sub_value})")
        if parts:
            css["filter"] = " ".join(parts)

    def _macro_transition(
        self,
        value: Any,
        subs: dict[str, Any],
        css: dict[str, str],
    ) -> None:
        """Pass-through: ``transition=<string>`` or sub-kwargs composed."""
        if value is not None:
            css["transition"] = str(value)
        for sub, sub_value in subs.items():
            css[f"transition-{sub.replace('_', '-')}"] = str(sub_value)

    def _macro_zoom(
        self,
        value: Any,
        subs: dict[str, Any],
        css: dict[str, str],
    ) -> None:
        """Pass-through: ``zoom=<value>``."""
        if value is not None:
            css["zoom"] = str(value)
        # zoom historically has no sub-kwargs; ignore them silently

    def _macro_shadow(
        self,
        value: Any,
        subs: dict[str, Any],
        css: dict[str, str],
    ) -> None:
        """Pass-through: ``shadow=<box-shadow value>``."""
        if value is not None:
            css["box-shadow"] = str(value)
        for sub, sub_value in subs.items():
            css[f"box-shadow-{sub.replace('_', '-')}"] = str(sub_value)

    def _macro_gradient(
        self,
        value: Any,
        subs: dict[str, Any],
        css: dict[str, str],
    ) -> None:
        """Pass-through: ``gradient="linear-gradient(...)"`` or shorthand."""
        if value is not None:
            css["background-image"] = str(value)
        # detailed gradient sub-kwargs deferred to a future iteration


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------

_ATTR_VALUE_ESCAPE = str.maketrans(
    {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"},
)


def _is_style_attr(name: str) -> bool:
    """Return True if ``name`` matches a CSS root or a ``root_*`` form."""
    if name in _STYLE_ROOTS:
        return True
    for root in _STYLE_ROOTS:
        if name.startswith(root + "_"):
            return True
    return False


def _parse_style_string(value: Any) -> dict[str, str]:
    """Parse a ``style="key: value; key: value"`` literal into a dict.

    Empty/blank entries are skipped. Whitespace is stripped. Properties
    seen multiple times: last one wins (rare in practice).
    """
    result: dict[str, str] = {}
    if not value:
        return result
    for entry in str(value).split(";"):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        key, val = entry.split(":", 1)
        result[key.strip()] = val.strip()
    return result


def _px(value: Any) -> str:
    """Append ``px`` to numeric values, pass strings through verbatim."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value}px"
    return str(value)
