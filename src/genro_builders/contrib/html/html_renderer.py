# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlRenderer — renderer for the HTML5 dialect.

Walks the source bag and produces HTML5 markup. Registered on
``HtmlBuilder`` under the ``"html"`` mode (decision 6+8 v0.4.0).
Exposed on the handler as ``handler.renderer`` (with
``handler.render(...)`` as shortcut).

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

from ...renderer import RendererBase

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "source", "track", "wbr",
})

#: Raw text elements: their content is CSS/JS, not HTML, so per the spec
#: it is emitted verbatim (no entity escaping). A ``>`` in a CSS combinator
#: or ``&&`` in JavaScript must survive unchanged.
_RAW_TEXT_TAGS = frozenset({"style", "script"})

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
    """Renderer for the HTML5 dialect.

    ``rendered_item`` emits the markup for one node. The walk is
    driven by the universal ``RendererBase.render`` on the base
    class: children fragments arrive already-rendered via ``item``.
    """

    mode = "html"

    def rendered_item(
        self,
        node: Any,
        item: Any,
        runtime_attrs: dict[str, Any],
        *,
        tag: str,
        xml: bool = True,
        pretty: bool = False,
        include_datapath: bool = False,
        **_extra: Any,
    ) -> str:
        """Emit the HTML5 fragment for ``node``.

        - ``tag``/``runtime_attrs`` are already resolved by the base
          ``_handle_meta`` (render_tag and render_attributes applied).
        - ``item`` is a list of already-rendered child fragments when
          the node's value is a Bag; a leaf value otherwise (``None``
          for empty leaves).
        - ``xml`` selects XHTML-style void tags (``<br/>`` vs
          ``<br>``).
        - ``pretty`` enables multi-line indented output (2 spaces per
          level).
        - ``include_datapath`` emits, next to each pointer-bound
          attribute, a ``data-<name>-pointer`` carrying its absolute
          datapath — the hook client-side code uses to write back.
        """
        attrs = self._format_attrs(runtime_attrs)
        if include_datapath:
            attrs += self._auto_id_attr(node, runtime_attrs)
            attrs += self._datapath_attrs(node)
        depth = self._node_depth(node)
        indent = "  " * depth if pretty else ""
        newline = "\n" if pretty else ""
        if tag in _VOID_TAGS:
            if xml:
                return f"{indent}<{tag}{attrs}/>{newline}"
            return f"{indent}<{tag}{attrs}>{newline}"
        if isinstance(item, list):
            body = "".join(item)
            return f"{indent}<{tag}{attrs}>{newline}{body}{indent}</{tag}>{newline}"
        if item is None:
            return f"{indent}<{tag}{attrs}></{tag}>{newline}"
        text = item if tag in _RAW_TEXT_TAGS else self._escape_text(item)
        return (
            f"{indent}<{tag}{attrs}>"
            f"{text}"
            f"</{tag}>{newline}"
        )

    # ------------------------------------------------------------------
    # Attribute formatting (HTML + CSS kwarg fusion)
    # ------------------------------------------------------------------

    def adapt_attrs(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Collapse CSS roots, ``style_*`` escapes and Genro macros into a
        single ``style`` entry, leaving plain HTML attributes (with the
        keyword-collision remap) as ordinary dict entries.

        Returns a dict — serialization is left to ``_format_attrs``. The
        output keys are final HTML attribute names; ``style`` carries the
        composed CSS text. The dialect escape ``html_<x>`` passes the
        literal attribute through untouched.
        """
        out: dict[str, Any] = {}
        style_attrs: dict[str, Any] = {}

        for raw_name, value in attrs.items():
            # 0. Dialect escape: ``html_<x>`` means "emit the literal HTML
            #    attribute ``<x>``", bypassing every interpretation below
            #    (CSS roots, macros, collision map). Lets ``html_type`` set
            #    ``type`` without shadowing the builtin, or ``html_width``
            #    set the HTML attribute instead of the CSS property.
            if raw_name.startswith(f"{self.builder._name}_"):
                out[self.adapt(raw_name)] = value
                continue

            # 1. Anything that contributes to the ``style`` entry (explicit
            #    style, style_* escapes, Genro macros, CSS roots) is handed
            #    to _adapt_style; the rest is a plain HTML attribute.
            if self._is_style_contribution(raw_name):
                style_attrs[raw_name] = value
                continue

            # 2. Plain HTML attribute. Keyword-collision names (``class_`` /
            #    ``_class``) are normalized later, at serialization, by
            #    _fix_pylike; structural meta-attrs are already filtered
            #    upstream in runtime_values.
            out[raw_name] = value

        style = self._adapt_style(style_attrs)
        if style:
            out["style"] = style
        return out

    def _is_style_contribution(self, raw_name: str) -> bool:
        """Whether ``raw_name`` feeds the composed ``style`` entry rather
        than being a plain HTML attribute."""
        if raw_name == "style":
            return True
        if raw_name.startswith("style_"):
            return True
        if raw_name in _GENRO_MACRO_NAMES:
            return True
        if "_" in raw_name and raw_name.split("_", 1)[0] in _GENRO_MACRO_NAMES:
            return True
        return _is_style_attr(raw_name)

    def _adapt_style(self, attrs: dict[str, Any]) -> str:
        """Compose the CSS ``style`` text from the style-contributing
        attributes (explicit ``style``, ``style_<prop>`` escapes, Genro
        macros, CSS roots). Returns the joined declaration string ("" if
        none)."""
        css: dict[str, str] = {}
        macro_value: dict[str, Any] = {}
        macro_subs: dict[str, dict[str, Any]] = {}

        for raw_name, value in attrs.items():
            # Explicit ``style="..."`` is parsed and seeded into css;
            # kwarg CSS will overwrite collisions later.
            if raw_name == "style":
                css.update(_parse_style_string(value))
                continue

            # ``style_<prop>`` escape: literal CSS, strip prefix.
            if raw_name.startswith("style_"):
                prop = raw_name[len("style_"):].replace("_", "-")
                css[prop] = self._css_value(value)
                continue

            # Top-level macro (``rounded=10``).
            if raw_name in _GENRO_MACRO_NAMES:
                macro_value[raw_name] = value
                continue

            # ``<macro>_<sub>`` sub-kwarg for a Genro macro (single
            # underscore). Macros never collide with CSS roots by design,
            # so the macro lookup wins over the root rule.
            if "_" in raw_name:
                head, sub = raw_name.split("_", 1)
                if head in _GENRO_MACRO_NAMES:
                    macro_subs.setdefault(head, {})[sub] = value
                    continue

            # CSS root / root_xxx rule.
            prop = raw_name.replace("_", "-")
            css[prop] = self._css_value(value)

        # Materialise Genro macros (may write into css).
        for macro_name in _GENRO_MACRO_NAMES:
            if macro_name in macro_value or macro_name in macro_subs:
                handler_method = getattr(self, f"_macro_{macro_name}")
                handler_method(
                    macro_value.get(macro_name),
                    macro_subs.get(macro_name, {}),
                    css,
                )

        return "; ".join(f"{k}: {v}" for k, v in css.items())

    def _format_attrs(self, attrs: dict[str, Any]) -> str:
        """Serialize an already-adapted attribute dict (see
        ``adapt_attrs``). The ``style`` entry is pre-composed CSS text;
        every other entry is a final HTML attribute name."""
        parts = []
        for name, value in attrs.items():
            if name == "style":
                parts.append(f' style="{value}"')
            else:
                parts.append(f' {name}="{self._html_attr_value(value)}"')
        return "".join(parts)

    def _auto_id_attr(self, node: Any, runtime_attrs: dict[str, Any]) -> str:
        """Emit ``id="<struct-path>"`` for a pointer-bound node, if needed.

        A node that carries at least one pointer (value or attribute) is
        potentially reactive: it may later receive a value change pushed
        from the server. To address it on the client (the future WebSocket
        patch channel: "node <id> changed"), it needs a stable per-node DOM
        identity. We use its structural path relative to the source root
        (``Bag.relative_path``) — unique by construction, stable while the
        structure does not change.

        No-op when the node has no pointer (static node), or when an ``id``
        is already present (the author's id wins). Only emitted under
        ``include_datapath`` (the reactive render mode).
        """
        if "id" in runtime_attrs:
            return ""
        if not node.pointers():
            return ""
        path = node.root_builder.source.relative_path(node)
        if path is None:
            return ""
        return f' id="{self._html_attr_value(path)}"'

    def _datapath_attrs(self, node: Any) -> str:
        """Emit ``data-<name>-pointer`` for every pointer-bound attribute.

        Reads the node's *original* attrs (``^``/``=`` strings, before
        resolution) and resolves each to its absolute datapath. The
        attribute name stays in its internal form (the ``data-<name>-
        pointer`` is a private write-back hook keyed by path, not by the
        HTML name), with only the dialect ``adapt`` escape applied.
        These are the write-back hooks client code reads on input events.
        """
        parts: list[str] = []
        for raw_name, value in node.attr.items():
            if not (isinstance(value, str) and value and value[0] in ("^", "=")):
                continue
            html_name = self.adapt(raw_name)
            path = node.abs_datapath(value)
            parts.append(f' data-{html_name}-pointer="{self._html_attr_value(path)}"')
        return "".join(parts)

    def _html_attr_value(self, value: Any) -> str:
        """Render a non-CSS attribute value (three-state booleans + escape)."""
        if value is True:
            return "true"
        if value is False:
            return "false"
        if value is None:
            return "null"
        return str(value).translate(_ATTR_VALUE_ESCAPE)

    def _css_value(self, value: Any) -> str:
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
    return any(name.startswith(root + "_") for root in _STYLE_ROOTS)


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
