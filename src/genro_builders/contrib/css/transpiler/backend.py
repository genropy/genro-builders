# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CSS->Python transpiler: parse CSS source and emit CssBuilder Python.

Pipeline mirrors the XSLT transpiler — two trees with a walk in
between::

    .css --tree-sitter-css--> CSS tree --walk--> Python AST --ast.unparse--> .py

``tree-sitter-css`` parses the CSS source into a tree; ``CssTranspiler``
walks it and builds a Python ``ast.Module`` calling the CssBuilder API;
``ast.unparse`` serializes that to Python source.

This module is gated behind the optional ``reverse`` extra. The
``tree_sitter`` and ``tree_sitter_css`` imports are wrapped in a
try/except so that importing ``genro_builders.contrib.css`` does not
force the heavy dependency on every user — only callers that invoke
the transpiler pay the cost.
"""

from __future__ import annotations

import ast
from typing import Any

try:
    import tree_sitter_css
    from tree_sitter import Language, Parser
except ImportError as exc:  # pragma: no cover - exercised only when extra missing
    _IMPORT_ERROR: ImportError | None = exc
    Language = None  # type: ignore[assignment,misc]
    Parser = None  # type: ignore[assignment,misc]
    tree_sitter_css = None  # type: ignore[assignment]
else:
    _IMPORT_ERROR = None

_INSTALL_HINT = (
    "Install the reverse extra: pip install 'genro-builders[reverse]'"
)

_PARSER: Any = None


def _get_parser() -> Any:
    """Return a lazily-built singleton ``tree_sitter.Parser`` for CSS."""
    global _PARSER
    if _IMPORT_ERROR is not None:
        raise ImportError(
            f"genro_builders.contrib.css reverse requires tree-sitter-css. "
            f"{_INSTALL_HINT}",
        ) from _IMPORT_ERROR
    if _PARSER is None:
        lang = Language(tree_sitter_css.language())  # type: ignore[misc]
        _PARSER = Parser(lang)  # type: ignore[misc]
    return _PARSER


def _parse_css(source: str) -> Any:
    """Parse a CSS source string and return the tree-sitter root node."""
    parser = _get_parser()
    tree = parser.parse(source.encode("utf-8"))
    return tree.root_node


# ---------------------------------------------------------------------------
# Selector → CssBuilder kwargs
# ---------------------------------------------------------------------------

def _selector_kwargs(selector_node: Any) -> dict[str, object]:
    """Map a tree-sitter selector node to ``selector(...)`` kwargs.

    Returns a dict suitable for ``selector(**kwargs)``. Falls back to
    ``{"raw": <text>}`` when the selector cannot be expressed via
    structured kwargs (combinators, multi-class + pseudo, etc.).
    """
    text = selector_node.text.decode()

    if selector_node.type in {
        "descendant_selector", "child_selector",
        "adjacent_sibling_selector", "sibling_selector",
    }:
        return {"raw": text}

    if selector_node.type == "selectors" and selector_node.named_child_count > 1:
        return {"raw": text}

    classes: list[str] = []
    tag: str | None = None
    sel_id: str | None = None
    attrs: dict[str, str | None] = {}
    pseudo_parts: list[str] = []
    functional_pseudo = False  # set when a :pseudo(args) is encountered

    def collect(n: Any) -> None:
        nonlocal tag, sel_id, functional_pseudo
        kind = n.type
        if kind == "class_selector":
            for c in n.named_children:
                if c.type == "class_name":
                    classes.append(c.text.decode())
                else:
                    collect(c)
            return
        if kind == "id_selector":
            for c in n.named_children:
                if c.type == "id_name":
                    sel_id = c.text.decode()
                else:
                    collect(c)
            return
        if kind in {"tag_name", "type_selector"}:
            tag = n.text.decode()
            return
        if kind == "universal_selector":
            pseudo_parts.append(n.text.decode())
            return
        if kind == "attribute_selector":
            attr_name: str | None = None
            attr_value: str | None = None
            for c in n.named_children:
                if c.type in {"attribute_name", "identifier"}:
                    attr_name = c.text.decode()
                elif c.type == "string_value":
                    s = c.text.decode()
                    attr_value = (
                        s[1:-1]
                        if len(s) >= 2 and s[0] in "\"'" and s[-1] in "\"'"
                        else s
                    )
                elif c.type == "plain_value":
                    attr_value = c.text.decode()
                else:
                    collect(c)
            if attr_name is not None:
                attrs[attr_name] = attr_value
            return
        if kind == "pseudo_class_selector":
            inner = None
            pseudo_name: str | None = None
            for c in n.named_children:
                if c.type in {"class_name", "identifier"}:
                    pseudo_name = c.text.decode()
                elif c.type in {"arguments", "pseudo_class_arguments"}:
                    pseudo_name = (pseudo_name or "") + c.text.decode()
                    functional_pseudo = True
                else:
                    inner = c
            if inner is not None:
                collect(inner)
            if pseudo_name is not None:
                pseudo_parts.append(":" + pseudo_name)
            return
        if kind == "pseudo_element_selector":
            element_name: str | None = None
            inner = None
            for c in n.named_children:
                if c.type in {"tag_name", "identifier"}:
                    if element_name is None:
                        element_name = c.text.decode()
                    else:
                        inner = c
                else:
                    inner = c
            if inner is not None:
                collect(inner)
            if element_name is not None:
                pseudo_parts.append("::" + element_name)
            return
        for c in n.named_children:
            collect(c)

    collect(selector_node)

    # Functional pseudos (:not, :nth-child, :has, ...) can carry
    # commas, parens and nested selectors that cannot survive the
    # structured class_ concatenation — emit the entire selector as
    # raw so the renderer's strict class regex doesn't reject it.
    if functional_pseudo:
        return {"raw": text}

    # Plain pseudo combined with tag/id/attr is also unsafe to
    # express structurally → raw.
    if pseudo_parts and (tag is not None or sel_id is not None or attrs):
        return {"raw": text}

    kwargs: dict[str, object] = {}
    if tag is not None:
        kwargs["tag"] = tag
    if sel_id is not None:
        kwargs["id"] = sel_id
    if pseudo_parts:
        joined_pseudo = "".join(pseudo_parts)
        if len(classes) == 1:
            kwargs["class_"] = classes[0] + joined_pseudo
        elif len(classes) > 1:
            return {"raw": text}
        else:
            kwargs["raw"] = joined_pseudo
    else:
        if len(classes) == 1:
            kwargs["class_"] = classes[0]
        elif len(classes) > 1:
            kwargs["classes"] = classes
    if attrs:
        kwargs["attr"] = attrs
    if not kwargs:
        kwargs["raw"] = text
    return kwargs


# ---------------------------------------------------------------------------
# Python AST construction helpers
# ---------------------------------------------------------------------------

def _value_to_ast(value: object) -> ast.expr:
    if isinstance(value, str):
        return ast.Constant(value=value)
    if isinstance(value, (int, float)):
        return ast.Constant(value=value)
    if value is None:
        return ast.Constant(value=None)
    if isinstance(value, list):
        return ast.List(elts=[_value_to_ast(v) for v in value], ctx=ast.Load())
    if isinstance(value, dict):
        return ast.Dict(
            keys=[ast.Constant(value=k) for k in value],
            values=[_value_to_ast(v) for v in value.values()],
        )
    return ast.Constant(value=repr(value))


def _kwargs_to_keywords(kwargs: dict[str, object]) -> list[ast.keyword]:
    return [ast.keyword(arg=k, value=_value_to_ast(v)) for k, v in kwargs.items()]


def _call(
    obj: str, method: str, *,
    kwargs: dict[str, object], args: list[object],
) -> ast.Call:
    return ast.Call(
        func=ast.Attribute(
            value=ast.Name(id=obj, ctx=ast.Load()),
            attr=method, ctx=ast.Load(),
        ),
        args=[_value_to_ast(a) for a in args],
        keywords=_kwargs_to_keywords(kwargs),
    )


def _assign_call(
    *, target: str, obj: str, method: str,
    kwargs: dict[str, object],
    args: list[object] | None = None,
) -> ast.stmt:
    return ast.Assign(
        targets=[ast.Name(id=target, ctx=ast.Store())],
        value=_call(obj, method, kwargs=kwargs, args=args or []),
    )


def _call_stmt(
    *, obj: str, method: str,
    kwargs: dict[str, object],
    args: list[object] | None = None,
) -> ast.stmt:
    return ast.Expr(value=_call(obj, method, kwargs=kwargs, args=args or []))


def _comment_stmt(text: str) -> ast.stmt:
    return ast.Expr(value=ast.Constant(value=f"# {text}"))


def _first(node: Any, type_name: str) -> Any | None:
    for c in node.children:
        if c.type == type_name:
            return c
    return None


def _kebab_to_snake(name: str) -> str:
    return name.replace("-", "_")


# ---------------------------------------------------------------------------
# CssTranspiler
# ---------------------------------------------------------------------------

class CssTranspiler:
    """Walk a tree-sitter CSS tree and emit an ``ast.Module`` whose
    execution rebuilds an equivalent CSS via ``CssBuilder``."""

    def __init__(self, *, class_name: str = "ReversedCss") -> None:
        self._class_name = class_name
        self._counter = 0

    def _fresh_name(self, base: str) -> str:
        self._counter += 1
        return f"{base}_{self._counter}"

    def transpile(self, css: str) -> ast.Module:
        """Parse ``css`` and return an ``ast.Module`` Python source AST.

        The emitted ``main(self, root)`` always opens a ``stylesheet``
        container as its first statement (``sheet = root.stylesheet()``)
        and uses it as the parent for all top-level constructs. This
        is uniform regardless of whether the source CSS contains
        ``@import`` directives — the assumption is that the reverse
        targets whole stylesheets, not isolated fragments.
        """
        self._counter = 0
        root = _parse_css(css)
        sheet_stmt = _assign_call(
            target="sheet", obj="root",
            method="stylesheet", kwargs={},
        )
        body: list[ast.stmt] = [sheet_stmt]
        for child in root.children:
            body.extend(self._stylesheet_child(
                child, parent_var="sheet", media=None, supports=None,
            ))
        main_func = ast.FunctionDef(
            name="main",
            args=ast.arguments(
                args=[ast.arg(arg="self"), ast.arg(arg="root")],
                posonlyargs=[], kwonlyargs=[], kw_defaults=[], defaults=[],
            ),
            body=body if body else [ast.Pass()],
            decorator_list=[],
        )
        class_def = ast.ClassDef(
            name=self._class_name,
            bases=[ast.Name(id="CssBuilder", ctx=ast.Load())],
            keywords=[],
            body=[main_func],
            decorator_list=[],
        )
        module = ast.Module(
            body=[
                ast.ImportFrom(
                    module="genro_builders.contrib.css",
                    names=[ast.alias(name="CssBuilder", asname=None)],
                    level=0,
                ),
                class_def,
            ],
            type_ignores=[],
        )
        ast.fix_missing_locations(module)
        return module

    def _stylesheet_child(
        self, node: Any, *, parent_var: str,
        media: str | None, supports: str | None,
    ) -> list[ast.stmt]:
        if node.type == "rule_set":
            return self._rule_set(
                node, parent_var=parent_var, media=media, supports=supports,
            )
        if node.type == "media_statement":
            return self._media_statement(
                node, parent_var=parent_var, outer_supports=supports,
            )
        if node.type == "supports_statement":
            return self._supports_statement(
                node, parent_var=parent_var, outer_media=media,
            )
        if node.type == "import_statement":
            return [self._import_statement(node, parent_var=parent_var)]
        if node.type in {"comment", "{", "}"}:
            return []
        text = node.text.decode().strip()
        if not text:
            return []
        return [_comment_stmt(f"unsupported: {node.type}: {text[:60]}")]

    def _import_statement(self, node: Any, *, parent_var: str) -> ast.stmt:
        """Emit ``parent.importcss(url=..., media=..., supports=..., layer=...)``.

        tree-sitter-css (0.25) recognises the ``url(...)`` / bare-string
        form and a trailing media-query. The ``layer(...)`` and
        ``supports(...)`` modifiers are not in the grammar yet and
        appear as ``ERROR`` nodes; when present we fall back to a
        ``raw=`` kwarg carrying the full at-rule text minus the
        leading ``@import`` so the user can hand-clean it.
        """
        url: str | None = None
        media: str | None = None
        has_error = False
        for child in node.named_children:
            if child.type == "call_expression":
                for c in child.named_children:
                    if c.type == "arguments":
                        for arg in c.named_children:
                            if arg.type == "string_value":
                                url = self._unquote(arg.text.decode())
                            elif arg.type == "plain_value":
                                url = arg.text.decode()
            elif child.type == "string_value" and url is None:
                url = self._unquote(child.text.decode())
            elif child.type in {
                "feature_query", "binary_query", "selector_query",
                "keyword_query", "parenthesized_query",
            }:
                media_text = (
                    (media + " " + child.text.decode())
                    if media is not None
                    else child.text.decode()
                )
                media = media_text.strip()
            elif child.type == "ERROR":
                has_error = True

        if url is None:
            return _comment_stmt(
                f"unsupported import_statement: {node.text.decode()[:80]}",
            )
        if has_error:
            # layer(...) / supports(...) modifiers are still ERROR
            # nodes in tree-sitter-css 0.25; emit a comment so the
            # user knows the at-rule was dropped and can patch it
            # by hand instead of producing a half-true call.
            full_text = node.text.decode().rstrip(";").strip()
            return _comment_stmt(
                f"layer/supports modifier not parsed, see source: {full_text[:80]}",
            )
        kwargs: dict[str, object] = {"url": url}
        if media is not None:
            kwargs["media"] = media
        return _call_stmt(obj=parent_var, method="importcss", kwargs=kwargs)

    def _unquote(self, text: str) -> str:
        """Strip matching wrapping quotes from a string literal."""
        if len(text) >= 2 and text[0] in "\"'" and text[-1] == text[0]:
            return text[1:-1]
        return text

    def _rule_set(
        self, node: Any, *, parent_var: str,
        media: str | None, supports: str | None,
    ) -> list[ast.stmt]:
        selectors_node = node.child_by_field_name("selector") or _first(node, "selectors")
        if selectors_node is None:
            return []
        block = _first(node, "block")
        entries = [c for c in selectors_node.named_children if c.type != ","]
        if len(entries) == 1:
            sel_kwargs = _selector_kwargs(entries[0])
            sel_var = self._fresh_name("s")
            stmts: list[ast.stmt] = [
                _assign_call(
                    target=sel_var, obj=parent_var,
                    method="selector", kwargs=sel_kwargs,
                ),
            ]
            stmts.extend(self._block_into(
                sel_var, block, media=media, supports=supports,
            ))
            return stmts
        list_var = self._fresh_name("sl")
        stmts = [_assign_call(target=list_var, obj=parent_var, method="selectorList", kwargs={})]
        for entry in entries:
            stmts.append(_call_stmt(
                obj=list_var, method="selector", kwargs=_selector_kwargs(entry),
            ))
        stmts.extend(self._block_into(
            list_var, block, media=media, supports=supports,
        ))
        return stmts

    def _block_into(
        self, parent_var: str, block: Any | None,
        *, media: str | None, supports: str | None,
    ) -> list[ast.stmt]:
        if block is None:
            return []
        property_kwargs: dict[str, object] = {}
        cssvar_calls: list[ast.stmt] = []
        nested_stmts: list[ast.stmt] = []
        for child in block.named_children:
            if child.type == "declaration":
                self._absorb_declaration(
                    child, property_kwargs, cssvar_calls, parent_var=parent_var,
                )
            elif child.type == "rule_set":
                nested_stmts.extend(self._rule_set(
                    child, parent_var=parent_var, media=None, supports=None,
                ))
            elif child.type == "media_statement":
                nested_stmts.extend(self._media_statement(
                    child, parent_var=parent_var, outer_supports=supports,
                ))
            elif child.type == "supports_statement":
                nested_stmts.extend(self._supports_statement(
                    child, parent_var=parent_var, outer_media=media,
                ))
        stmts: list[ast.stmt] = []
        if property_kwargs or media is not None or supports is not None:
            rule_kwargs: dict[str, object] = dict(property_kwargs)
            if media is not None:
                rule_kwargs["media"] = media
            if supports is not None:
                rule_kwargs["supports"] = supports
            stmts.append(_call_stmt(obj=parent_var, method="rule", kwargs=rule_kwargs))
        stmts.extend(cssvar_calls)
        stmts.extend(nested_stmts)
        return stmts

    def _media_statement(
        self, node: Any, *, parent_var: str, outer_supports: str | None,
    ) -> list[ast.stmt]:
        cond = self._media_condition(node)
        block = _first(node, "block")
        if block is None:
            return []
        stmts: list[ast.stmt] = []
        for child in block.named_children:
            if child.type == "rule_set":
                stmts.extend(self._rule_set(
                    child, parent_var=parent_var,
                    media=cond, supports=outer_supports,
                ))
            elif child.type == "media_statement":
                stmts.extend(self._media_statement(
                    child, parent_var=parent_var, outer_supports=outer_supports,
                ))
            elif child.type == "supports_statement":
                stmts.extend(self._supports_statement(
                    child, parent_var=parent_var, outer_media=cond,
                ))
        return stmts

    def _media_condition(self, node: Any) -> str:
        text: str = node.text.decode()
        prefix = "@media"
        if text.startswith(prefix):
            text = text[len(prefix):].lstrip()
        brace_at = text.find("{")
        return text[:brace_at].strip() if brace_at != -1 else text.strip()

    def _supports_statement(
        self, node: Any, *, parent_var: str, outer_media: str | None,
    ) -> list[ast.stmt]:
        cond = self._supports_condition(node)
        block = _first(node, "block")
        if block is None:
            return []
        stmts: list[ast.stmt] = []
        for child in block.named_children:
            if child.type == "rule_set":
                stmts.extend(self._rule_set(
                    child, parent_var=parent_var,
                    media=outer_media, supports=cond,
                ))
            elif child.type == "supports_statement":
                stmts.extend(self._supports_statement(
                    child, parent_var=parent_var, outer_media=outer_media,
                ))
            elif child.type == "media_statement":
                stmts.extend(self._media_statement(
                    child, parent_var=parent_var, outer_supports=cond,
                ))
        return stmts

    def _supports_condition(self, node: Any) -> str:
        text: str = node.text.decode()
        prefix = "@supports"
        if text.startswith(prefix):
            text = text[len(prefix):].lstrip()
        brace_at = text.find("{")
        return text[:brace_at].strip() if brace_at != -1 else text.strip()

    def _absorb_declaration(
        self, node: Any,
        property_kwargs: dict[str, object],
        cssvar_calls: list[ast.stmt],
        *, parent_var: str,
    ) -> None:
        prop_node = _first(node, "property_name")
        if prop_node is None:
            return
        prop = prop_node.text.decode()
        value = self._declaration_value(node)
        if prop.startswith("--"):
            name = prop.removeprefix("--")
            cssvar_calls.append(_call_stmt(
                obj=parent_var, method="cssvar",
                args=[name], kwargs={"value": value},
            ))
        else:
            property_kwargs[_kebab_to_snake(prop)] = value

    def _declaration_value(self, node: Any) -> str:
        text: str = node.text.decode().rstrip(";").rstrip()
        _, _, rest = text.partition(":")
        return rest.strip()
