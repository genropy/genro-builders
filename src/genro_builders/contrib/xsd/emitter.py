# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XsdEmitter — turn a populated XsdBuilder source tree into .py source.

The third face of the single pivot: after :class:`~.reader.XsdReader` has
imported a schema into a builder (or after any builder has built its
tree), the emitter walks that tree and writes the Python that recreates
it — the schema "as if you had written it in XsdBuilder by hand". Re-run
that .py, render it, and you get an equipollent schema back.

Two styles:

``style="literal"`` (default): one variable per container node, one call
per node, 1:1 with the tree in appearance order — predictable, and the
exact chain the author would type. Attribute values ride through verbatim
(``fixed_attr_items`` gives the user attributes, the grammar meta like
``ns`` filtered out); a node's text value becomes the first positional
argument.

``style="idiomatic"``: readability pass over the same tree — semantic
variable names (from ``name``/``type`` instead of a counter), named
``complexType``/``simpleType`` grouped into dedicated methods, chaining
for single-use nodes, a shared ``enumerated()`` helper for repeated
enumeration/annotation/documentation triplets, and ``@component`` aliases
for named types so ``seq.TipoCassaType(name="Tipo")`` replaces
``seq.element(name="Tipo", type="TipoCassaType")``. Declaration order
between independent top-level types is free (XSD resolves them by name);
order INSIDE a ``sequence``/``choice`` is always preserved exactly.

``components=True`` is reserved for folding reused named types into
``@component`` definitions as a semantic pass over the LITERAL style — a
different, not yet implemented, axis from ``style``.
"""

from __future__ import annotations

import re
from typing import Any

_HEADER = "# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0"

_TYPE_TAGS = ("complexType", "simpleType")

_ENUMERATED_METHOD = '''    def enumerated(self, restriction, values):
        """Add one xs:enumeration per value; value may be a code or (code, doc)."""
        for item in values:
            code, doc = item if isinstance(item, tuple) else (item, None)
            node = restriction.enumeration(value=code)
            if doc:
                node.annotation().documentation(doc)
'''


class XsdEmitter:
    """Emit Python source recreating a builder's source tree.

    Construction takes the builder whose tree is walked (stored as
    ``self.builder`` per the parent-passes-self convention)."""

    def __init__(self, builder: Any) -> None:
        self.builder = builder

    def emit(
        self,
        class_name: str = "GeneratedSchema",
        components: bool = False,
        style: str = "literal",
    ) -> str:
        """Return standalone Python source: a ``class_name(XsdBuilder)`` whose
        ``main`` rebuilds the tree.

        ``style="literal"`` (default) is the 1:1 transcription. ``style=
        "idiomatic"`` applies the readability pass described in the module
        docstring. ``components=True`` (a separate, not yet implemented,
        axis) is an explicit error rather than a silent no-op."""
        if components:
            raise NotImplementedError(
                "components=True (fold reused types into @component) is not "
                "implemented yet; use the literal form (components=False)"
            )
        if style == "literal":
            body = _LiteralPass().run(self.builder.source)
            extra_methods: list[str] = []
        elif style == "idiomatic":
            pass_ = _IdiomaticPass()
            body = pass_.run(self.builder.source)
            extra_methods = pass_.extra_methods()
        else:
            raise ValueError(f"unknown style {style!r}; use 'literal' or 'idiomatic'")
        return self._assemble(class_name, body, extra_methods)

    # ------------------------------------------------------------------

    def _assemble(
        self, class_name: str, body_lines: list[str], extra_methods: list[str],
    ) -> str:
        lines = [
            _HEADER,
            f'"""Generated XSD schema recreated as {class_name}."""',
            "from __future__ import annotations",
            "",
            "from genro_builders.contrib.xsd import XsdBuilder",
        ]
        if any("@component" in m for m in extra_methods):
            lines[-1] += "\nfrom genro_builders.builder import component"
        lines.extend([
            "",
            "",
            f"class {class_name}(XsdBuilder):",
        ])
        for method in extra_methods:
            lines.append(method)
        lines.append("    def main(self, root):")
        lines.extend(f"        {ln}" for ln in body_lines)
        lines.extend([
            "",
            "",
            'if __name__ == "__main__":',
            f"    page = {class_name}()",
            "    page.create()",
            "    print(page.render(target=False, doc_header=True, pretty=True))",
        ])
        return "\n".join(lines) + "\n"


def _is_bag(value: Any) -> bool:
    """True when a node's value is a child Bag (a container), not a leaf."""
    return value is not None and not isinstance(value, (str, int, float, bool))


def _children(node: Any) -> list[Any]:
    return list(node.value) if _is_bag(node.value) else []


class _LiteralPass:
    """One call per node, one var per container, counter-named, in
    appearance order — the existing, unchanged default behaviour."""

    def __init__(self) -> None:
        self.counters: dict[str, int] = {}

    def run(self, source: Any) -> list[str]:
        lines: list[str] = []
        for node in source:
            self._emit_node(node, "root", lines)
        return lines or ["pass"]

    def _emit_node(self, node: Any, parent_var: str, lines: list[str]) -> None:
        tag = node.node_tag
        attrs = dict(node.fixed_attr_items())
        text = node.value if isinstance(node.value, str) else None
        children = _children(node)

        call = _format_call(parent_var, tag, text, attrs)

        if children:
            var = self._fresh_var(tag)
            lines.append(f"{var} = {call}")
            for child in children:
                self._emit_node(child, var, lines)
        else:
            lines.append(call)

    def _fresh_var(self, tag: str) -> str:
        n = self.counters.get(tag, 0)
        self.counters[tag] = n + 1
        return f"{tag}_{n}"


def _format_call(
    parent_var: str, tag: str, text: str | None, attrs: dict[str, Any],
) -> str:
    args = []
    if text is not None:
        args.append(repr(text))
    args.extend(f"{name}={value!r}" for name, value in attrs.items())
    return f"{parent_var}.{tag}({', '.join(args)})"


_SLUG_INVALID = re.compile(r"[^0-9a-zA-Z_]+")
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


class _IdiomaticPass:
    """Readability pass: semantic names, grouped named types, chaining
    for single-use nodes, enumerated() for repeated enumeration runs,
    and @component aliases for named types.

    Declaration order between independent top-level complexType/simpleType
    is free (XSD resolves them by name, not position) — grouped in
    dedicated methods regardless of where they appeared in the source.
    Order INSIDE any sequence/choice is walked exactly as found.
    """

    def __init__(self) -> None:
        self._slug_used: dict[str, int] = {}
        self._named_types: dict[str, Any] = {}
        self._used_as_component: set[str] = set()
        self._needs_enumerated = False
        self._type_methods: list[str] = []

    def run(self, source: Any) -> list[str]:
        top_nodes = list(source)
        lines: list[str] = []
        for node in top_nodes:
            if node.node_tag == "schema":
                self._emit_schema(node, lines)
            else:
                self._emit_node(node, "root", lines)
        return lines or ["pass"]

    def _emit_schema(self, schema_node: Any, lines: list[str]) -> None:
        schema_children = _children(schema_node)
        typed = [n for n in schema_children if n.node_tag in _TYPE_TAGS]
        other = [n for n in schema_children if n.node_tag not in _TYPE_TAGS]

        self._named_types = {
            attrs["name"]: node
            for node in typed
            for attrs in [dict(node.fixed_attr_items())]
            if "name" in attrs
        }

        attrs = dict(schema_node.fixed_attr_items())
        call = _format_call("root", "schema", None, attrs)
        var = self._slug(schema_node, attrs)
        lines.append(f"{var} = {call}")
        for child in other:
            self._emit_node(child, var, lines)

        complex_nodes = [n for n in typed if n.node_tag == "complexType"]
        simple_nodes = [n for n in typed if n.node_tag == "simpleType"]
        if complex_nodes:
            self._type_methods.append(
                self._emit_type_group_method("complex_types", var, complex_nodes),
            )
            lines.append(f"self.complex_types({var})")
        if simple_nodes:
            self._type_methods.append(
                self._emit_type_group_method("simple_types", var, simple_nodes),
            )
            lines.append(f"self.simple_types({var})")

    def _emit_type_group_method(self, method_name: str, param: str, nodes: list[Any]) -> str:
        body: list[str] = []
        for node in nodes:
            self._emit_node(node, param, body)
        indented = "\n".join(f"        {ln}" for ln in body)
        return f"    def {method_name}(self, {param}):\n{indented}\n"

    def extra_methods(self) -> list[str]:
        methods: list[str] = []
        if self._needs_enumerated:
            methods.append(_ENUMERATED_METHOD)
        methods.extend(self._type_methods)
        for name in sorted(self._used_as_component):
            methods.append(
                "    @component\n"
                f"    def {name}(self, root, name, **attrs):\n"
                f'        root.element(name=name, type="{name}", **attrs)\n'
            )
        return methods

    # -- naming ------------------------------------------------------

    def _slug(self, node: Any, attrs: dict[str, Any]) -> str:
        base = attrs.get("name") or attrs.get("type") or node.node_tag
        snake = _CAMEL_BOUNDARY.sub("_", base)
        snake = _SLUG_INVALID.sub("_", snake).strip("_").lower()
        if not snake:
            snake = node.node_tag.lower()
        if snake[0].isdigit():
            snake = f"_{snake}"
        n = self._slug_used.get(snake, 0)
        self._slug_used[snake] = n + 1
        return snake if n == 0 else f"{snake}_{n}"

    # -- enumeration run detection ------------------------------------

    def _enumeration_value(self, enum_node: Any) -> tuple[str | None, str | None]:
        attrs = dict(enum_node.fixed_attr_items())
        code = attrs.get("value")
        doc_children = _children(enum_node)
        doc = None
        if len(doc_children) == 1 and doc_children[0].node_tag == "annotation":
            doc_grandchildren = _children(doc_children[0])
            if (
                len(doc_grandchildren) == 1
                and doc_grandchildren[0].node_tag == "documentation"
                and isinstance(doc_grandchildren[0].value, str)
            ):
                doc = doc_grandchildren[0].value
        return code, doc

    def _is_plain_enumeration(self, enum_node: Any) -> bool:
        """True when this enumeration node has no more than the
        annotation/documentation shape ``_enumeration_value`` understands
        (nothing else worth walking individually)."""
        children = _children(enum_node)
        if not children:
            return True
        if len(children) != 1 or children[0].node_tag != "annotation":
            return False
        grandchildren = _children(children[0])
        return (
            len(grandchildren) == 1
            and grandchildren[0].node_tag == "documentation"
            and isinstance(grandchildren[0].value, str)
            and not _children(grandchildren[0])
        )

    # -- emission ------------------------------------------------------

    def _emit_node(self, node: Any, parent_var: str, lines: list[str]) -> None:
        tag = node.node_tag
        attrs = dict(node.fixed_attr_items())
        children = _children(node)

        if tag == "restriction" and self._emit_restriction(node, attrs, children, parent_var, lines):
            return

        if tag == "element" and self._emit_typed_element(attrs, parent_var, lines):
            return

        text = node.value if isinstance(node.value, str) else None
        chain, tail_children, branch_node = self._build_chain(node, tag, text, attrs, parent_var)
        if chain is not None and not tail_children:
            lines.append(chain)
            return
        if chain is not None:
            # The chain stalled on a branching node: emit the collapsed
            # prefix as a variable NAMED AFTER branch_node (the last node
            # folded into the chain — what the variable actually holds,
            # not the first node the chain started from), then recurse on
            # its own children (dropped from the chain itself).
            branch_attrs = dict(branch_node.fixed_attr_items())
            var = self._slug(branch_node, branch_attrs)
            lines.append(f"{var} = {chain}")
            for child in tail_children:
                self._emit_node(child, var, lines)
            return

        call = _format_call(parent_var, tag, text, attrs)
        if children:
            var = self._slug(node, attrs)
            lines.append(f"{var} = {call}")
            for child in children:
                self._emit_node(child, var, lines)
        else:
            lines.append(call)

    def _emit_typed_element(self, attrs: dict[str, Any], parent_var: str, lines: list[str]) -> bool:
        """``element`` referencing a named type of THIS schema becomes a
        call to the type's own @component alias instead of ``element(
        type=...)``. Builtin (``xs:*``) or unknown types fall through."""
        type_name = attrs.get("type")
        if type_name not in self._named_types:
            return False
        self._used_as_component.add(type_name)
        rest = {k: v for k, v in attrs.items() if k != "type"}
        args = ", ".join(f"{k}={v!r}" for k, v in rest.items())
        lines.append(f"{parent_var}.{type_name}({args})")
        return True

    def _emit_restriction(
        self, node: Any, attrs: dict[str, Any], children: list[Any],
        parent_var: str, lines: list[str],
    ) -> bool:
        """Emit a restriction, collapsing runs of 2+ plain ``enumeration``
        children into ``self.enumerated(var, [...])``. Returns True when
        this node has been fully handled (caller should not fall through
        to the generic path)."""
        run_start = next(
            (i for i, c in enumerate(children) if c.node_tag == "enumeration"), None,
        )
        if run_start is None:
            return False
        run_end = run_start
        while run_end < len(children) and children[run_end].node_tag == "enumeration":
            run_end += 1
        run = children[run_start:run_end]
        if len(run) < 2 or not all(self._is_plain_enumeration(c) for c in run):
            return False

        call = _format_call(parent_var, "restriction", None, attrs)
        var = self._slug(node, attrs)
        lines.append(f"{var} = {call}")
        for child in children[:run_start]:
            self._emit_node(child, var, lines)

        values = [self._enumeration_value(c) for c in run]
        if all(doc is None for _, doc in values):
            literal = "[" + ", ".join(repr(code) for code, _ in values) + "]"
        else:
            literal = "[" + ", ".join(repr((code, doc)) for code, doc in values) + "]"
        lines.append(f"self.enumerated({var}, {literal})")
        self._needs_enumerated = True

        for child in children[run_end:]:
            self._emit_node(child, var, lines)
        return True

    def _build_chain(
        self, node: Any, tag: str, text: str | None, attrs: dict[str, Any], parent_var: str,
    ) -> tuple[str | None, list[Any], Any]:
        """A node with exactly one child, recursively, collapses into one
        chained call — no intermediate variables. Returns ``(chain,
        tail_children, branch_node)``: ``tail_children`` is empty when the
        chain ran down to a true leaf, or holds ``branch_node``'s own
        children when the chain stalled on a node with 0 or 2+ children
        (the caller must then recurse on them itself, under a variable
        bound to ``branch_node`` — the LAST node folded into the chain,
        not the first — so the name matches what the variable actually
        holds)."""
        segments = [_format_call("", tag, text, attrs)[1:]]  # drop parent_var
        current = node
        while True:
            children = _children(current)
            if len(children) != 1:
                return (None, [], None) if len(segments) < 2 else (
                    f"{parent_var}." + ".".join(segments), children, current,
                )
            child = children[0]
            child_tag = child.node_tag
            if child_tag == "restriction" and self._has_enumeration_run(child):
                return f"{parent_var}." + ".".join(segments), children, current
            child_attrs = dict(child.fixed_attr_items())
            if child_tag == "element" and child_attrs.get("type") in self._named_types:
                return f"{parent_var}." + ".".join(segments), children, current
            child_text = child.value if isinstance(child.value, str) else None
            segments.append(_format_call("", child_tag, child_text, child_attrs)[1:])
            current = child

    def _has_enumeration_run(self, restriction_node: Any) -> bool:
        children = _children(restriction_node)
        run = [c for c in children if c.node_tag == "enumeration"]
        return len(run) >= 2 and all(self._is_plain_enumeration(c) for c in run)


if __name__ == "__main__":
    from genro_builders.contrib.xsd import XsdBuilder
    from genro_builders.contrib.xsd.reader import XsdReader

    XS = "http://www.w3.org/2001/XMLSchema"
    XSD = (
        f'<xs:schema xmlns:xs="{XS}" targetNamespace="urn:demo" '
        'elementFormDefault="qualified">'
        '<xs:element name="Person"><xs:complexType><xs:sequence>'
        '<xs:element name="Name" type="xs:string"/>'
        '<xs:element name="Age" type="xs:integer" minOccurs="0"/>'
        "</xs:sequence></xs:complexType></xs:element></xs:schema>"
    )
    builder = XsdReader(XsdBuilder()).read(XSD)
    print(XsdEmitter(builder).emit(class_name="PersonSchema"))
