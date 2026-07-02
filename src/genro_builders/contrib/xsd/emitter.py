# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XsdEmitter — turn a populated XsdBuilder source tree into .py source.

The third face of the single pivot: after :class:`~.reader.XsdReader` has
imported a schema into a builder (or after any builder has built its
tree), the emitter walks that tree and writes the Python that recreates
it — the schema "as if you had written it in XsdBuilder by hand". Re-run
that .py, render it, and you get an equipollent schema back.

Literal by default: one variable per container node, one call per node,
1:1 with the tree — predictable, and the exact chain the author would
type. Attribute values ride through verbatim (``fixed_attr_items`` gives
the user attributes, the grammar meta like ``ns`` filtered out); a node's
text value becomes the first positional argument.

``components=True`` is reserved for folding reused named types into
``@component`` definitions — a semantic pass left for later; the literal
form is the verifiable base an optional LLM step can then refine.
"""

from __future__ import annotations

from typing import Any

_HEADER = "# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0"


class XsdEmitter:
    """Emit Python source recreating a builder's source tree.

    Construction takes the builder whose tree is walked (stored as
    ``self.builder`` per the parent-passes-self convention)."""

    def __init__(self, builder: Any) -> None:
        self.builder = builder

    def emit(self, class_name: str = "GeneratedSchema", components: bool = False) -> str:
        """Return standalone Python source: a ``class_name(XsdBuilder)`` whose
        ``main`` rebuilds the tree.

        ``components=False`` (default) is the literal transcription. The
        component-folding pass is not implemented yet; asking for it is an
        explicit error rather than a silent no-op."""
        if components:
            raise NotImplementedError(
                "components=True (fold reused types into @component) is not "
                "implemented yet; use the literal form (components=False)"
            )
        body = self._emit_main_body()
        return self._assemble(class_name, body)

    # ------------------------------------------------------------------

    def _assemble(self, class_name: str, body_lines: list[str]) -> str:
        lines = [
            _HEADER,
            f'"""Generated XSD schema recreated as {class_name}."""',
            "from __future__ import annotations",
            "",
            "from genro_builders.builder import BuilderHandler",
            "from genro_builders.contrib.xsd import XsdBuilder",
            "",
            "",
            f"class {class_name}(XsdBuilder):",
            "    def main(self, root):",
        ]
        lines.extend(f"        {ln}" for ln in body_lines)
        lines.extend([
            "",
            "",
            'if __name__ == "__main__":',
            f"    page = {class_name}()",
            "    BuilderHandler().add_builder(page)",
            "    print(page.render(target=False, doc_header=True, pretty=True))",
        ])
        return "\n".join(lines) + "\n"

    def _emit_main_body(self) -> list[str]:
        """Walk the source tree, one statement per node. Returns the body
        lines of ``main`` (each indented later by ``_assemble``)."""
        lines: list[str] = []
        counters: dict[str, int] = {}
        for node in self.builder.source:
            self._emit_node(node, parent_var="root", lines=lines, counters=counters)
        return lines or ["pass"]

    def _emit_node(
        self,
        node: Any,
        parent_var: str,
        lines: list[str],
        counters: dict[str, int],
    ) -> None:
        """Emit ``<var> = <parent_var>.<tag>(<args>)`` and recurse on any
        children. A childless, valueless node emits a bare call (no var)."""
        tag = node.node_tag
        attrs = dict(node.fixed_attr_items())
        text = node.value if isinstance(node.value, str) else None
        has_children = _is_bag(node.value)

        call = self._format_call(parent_var, tag, text, attrs)

        if has_children:
            var = self._fresh_var(tag, counters)
            lines.append(f"{var} = {call}")
            for child in node.value:
                self._emit_node(child, var, lines, counters)
        else:
            lines.append(call)

    def _format_call(
        self, parent_var: str, tag: str, text: str | None, attrs: dict[str, Any],
    ) -> str:
        args = []
        if text is not None:
            args.append(repr(text))
        args.extend(f"{name}={value!r}" for name, value in attrs.items())
        return f"{parent_var}.{tag}({', '.join(args)})"

    def _fresh_var(self, tag: str, counters: dict[str, int]) -> str:
        """A readable, unique variable name per node: ``element_0``, ..."""
        n = counters.get(tag, 0)
        counters[tag] = n + 1
        return f"{tag}_{n}"


def _is_bag(value: Any) -> bool:
    """True when a node's value is a child Bag (a container), not a leaf."""
    return value is not None and not isinstance(value, (str, int, float, bool))


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
