# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""PythonGenerator — render a NamespaceModel into Python source.

The output is a standalone module that declares one class with
``@element`` methods for every element in the model. The generated
class is meant to be used as a **mixin**: a concrete builder pairs it
with :class:`~genro_builders.builder.BagBuilderBase`, optionally
mixed with a renderer registration in ``__init__``. This matches the
``Html5Elements`` / ``HtmlBuilder`` pattern in ``contrib/html``.

Constraints recorded in the model but **not** emitted as validators
(because the current grammar does not yet support them) are surfaced
as comments next to the relevant ``@element`` so a future grammar
extension knows where to plug them in. See ``finaldoc.md`` of subtask
``schema_builder_repair`` for the full list of gaps.
"""

from __future__ import annotations

import keyword
import re
from io import StringIO

from .model import (
    ChildModel,
    ElementModel,
    NamespaceModel,
    SimpleConstraint,
)


class PythonGenerator:
    """Render a :class:`NamespaceModel` into Python source text.

    The generator is deterministic: the same model produces byte-for-
    byte identical output. This is exploited by tests to verify
    idempotence of the codegen pipeline.
    """

    def render(
        self,
        model: NamespaceModel,
        class_name: str,
        module_docstring: str | None = None,
    ) -> str:
        """Return the full Python source for the generated mixin."""
        out = StringIO()
        self._write_header(out, model, class_name, module_docstring)
        self._write_imports(out, model)
        self._write_class(out, model, class_name)
        return out.getvalue()

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _write_header(
        self,
        out: StringIO,
        model: NamespaceModel,
        class_name: str,
        module_docstring: str | None,
    ) -> None:
        out.write("# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0\n")
        out.write("# GENERATED FILE - DO NOT EDIT MANUALLY.\n")
        out.write(
            "# Regenerate with: python -m genro_builders.contrib.xsd.codegen "
            "--xsd <path> --class-name "
            f"{class_name} --output <path>\n"
        )
        if model.target_namespace:
            out.write(f"# Source targetNamespace: {model.target_namespace}\n")
        out.write('"""')
        if module_docstring:
            out.write(module_docstring.strip())
        else:
            out.write(f"Auto-generated element mixin for {class_name}.")
        out.write('"""\n\n')
        out.write("from __future__ import annotations\n\n")

    def _write_imports(self, out: StringIO, model: NamespaceModel) -> None:
        uses_regex = self._uses_regex(model)
        uses_range = self._uses_range(model)
        uses_annotated = uses_regex or uses_range
        uses_literal = self._uses_literal(model)
        uses_decimal = self._uses_decimal(model)

        typing_imports: list[str] = []
        if uses_annotated:
            typing_imports.append("Annotated")
        if uses_literal:
            typing_imports.append("Literal")
        if typing_imports:
            out.write(f"from typing import {', '.join(typing_imports)}\n")

        if uses_decimal:
            out.write("from decimal import Decimal\n")

        if typing_imports or uses_decimal:
            out.write("\n")

        builder_imports: list[str] = ["element"]
        if uses_regex:
            builder_imports.append("Regex")
        if uses_range:
            builder_imports.append("Range")
        out.write(f"from genro_builders.builder import {', '.join(builder_imports)}\n\n\n")

    def _write_class(
        self,
        out: StringIO,
        model: NamespaceModel,
        class_name: str,
    ) -> None:
        out.write(f"class {class_name}:\n")
        ns = model.target_namespace or "<no namespace>"
        out.write(
            f'    """Element mixin generated from XSD namespace ``{ns}``.\n\n'
        )
        out.write("    Pair with ``BagBuilderBase`` in a concrete builder class.\n")
        if model.imports:
            out.write(
                "\n    NOTE: the source XSD declares additional namespace imports "
                "that are not introspected by the current codegen:\n"
            )
            for imp in model.imports:
                out.write(f"        - {imp.uri}\n")
        out.write('    """\n\n')

        for element in model.elements:
            self._write_element(out, element)

    def _write_element(self, out: StringIO, element: ElementModel) -> None:
        sub_tags = self._build_sub_tags(element.children)
        call_args = self._build_call_args(element)
        notes = self._collect_notes(element)
        method_name, alias = self._safe_method_name(element.name)

        for note in notes:
            out.write(f"    # NOTE: {note}\n")

        if alias and alias != method_name:
            out.write(f"    # XSD tag: {alias}\n")

        decorator_args: list[str] = []
        if alias and alias != method_name:
            decorator_args.append(f"tags={alias!r}")
        if sub_tags is not None:
            decorator_args.append(f"sub_tags={sub_tags!r}")

        if not decorator_args:
            out.write("    @element()\n")
        else:
            joined = ",\n        ".join(decorator_args)
            out.write(f"    @element(\n        {joined},\n    )\n")

        signature = self._build_signature(element, call_args)
        doc = self._build_docstring(element, call_args)
        out.write(f"    def {method_name}({signature}):\n")
        if doc:
            out.write(f'        """{doc}"""\n')
        out.write("        ...\n\n")

    # ------------------------------------------------------------------
    # sub_tags
    # ------------------------------------------------------------------

    def _build_sub_tags(self, children: list[ChildModel]) -> str | None:
        if not children:
            return None
        # Collapse duplicate names by widest range.
        merged: dict[str, tuple[int, int | None]] = {}
        for ch in children:
            prev = merged.get(ch.name)
            if prev is None:
                merged[ch.name] = (ch.min_occurs, ch.max_occurs)
                continue
            pmin, pmax = prev
            new_min = min(pmin, ch.min_occurs)
            new_max = None if pmax is None or ch.max_occurs is None else max(pmax, ch.max_occurs)
            merged[ch.name] = (new_min, new_max)

        parts: list[str] = []
        for name, (min_o, max_o) in merged.items():
            parts.append(_format_sub_tag(name, min_o, max_o))
        return ",".join(parts)

    # ------------------------------------------------------------------
    # call_args (attributes + simpleContent node_value)
    # ------------------------------------------------------------------

    def _build_call_args(self, element: ElementModel) -> list[tuple[str, str, bool]]:
        """Return (param_name, annotation_expr, has_validator) triples.

        ``has_validator`` is True when the generated annotation uses
        ``Annotated[...]`` with a Regex/Range, so callers know whether
        an ``Annotated`` import is needed (currently always inlined).
        """
        args: list[tuple[str, str, bool]] = []
        if element.text_constraint is not None:
            ann, has_val = self._annotation_for(element.text_constraint)
            args.append(("node_value", ann, has_val))
        for attr in element.attrs:
            if attr.constraint is None:
                ann = "str"
                args.append((attr.name, ann, False))
                continue
            ann, has_val = self._annotation_for(attr.constraint)
            args.append((attr.name, ann, has_val))
        return args

    def _annotation_for(self, constraint: SimpleConstraint) -> tuple[str, bool]:
        if constraint.base == "enum" and constraint.enum_values:
            literal = ", ".join(repr(v) for v in constraint.enum_values)
            return (f"Literal[{literal}]", False)

        py_type = {
            "string": "str",
            "int": "int",
            "decimal": "Decimal",
            "bool": "bool",
        }.get(constraint.base, "str")

        validators: list[str] = []
        if constraint.pattern:
            validators.append(f"Regex({constraint.pattern!r})")
        if constraint.min_inclusive is not None or constraint.max_inclusive is not None:
            kwargs: list[str] = []
            if constraint.min_inclusive is not None:
                kwargs.append(f"ge={float(constraint.min_inclusive)!r}")
            if constraint.max_inclusive is not None:
                kwargs.append(f"le={float(constraint.max_inclusive)!r}")
            validators.append(f"Range({', '.join(kwargs)})")

        if not validators:
            return (py_type, False)

        joined = ", ".join(validators)
        return (f"Annotated[{py_type}, {joined}]", True)

    # ------------------------------------------------------------------
    # Notes (gaps surfaced to the reader)
    # ------------------------------------------------------------------

    def _collect_notes(self, element: ElementModel) -> list[str]:
        notes: list[str] = []
        for constraint, label in self._iter_constraints(element):
            for txt in _constraint_notes(constraint, label):
                notes.append(txt)
        return notes

    def _iter_constraints(
        self,
        element: ElementModel,
    ) -> list[tuple[SimpleConstraint, str]]:
        pairs: list[tuple[SimpleConstraint, str]] = []
        if element.text_constraint is not None:
            pairs.append((element.text_constraint, "node_value"))
        for attr in element.attrs:
            if attr.constraint is not None:
                pairs.append((attr.constraint, attr.name))
        return pairs

    # ------------------------------------------------------------------
    # Signature and docstring
    # ------------------------------------------------------------------

    def _build_signature(
        self,
        element: ElementModel,
        call_args: list[tuple[str, str, bool]],
    ) -> str:
        parts = ["self"]
        for name, ann, _ in call_args:
            safe = _safe_param_name(name)
            parts.append(f"{safe}: {ann} = None")
        return ", ".join(parts)

    def _build_docstring(
        self,
        element: ElementModel,
        call_args: list[tuple[str, str, bool]],
    ) -> str:
        bits: list[str] = []
        if element.documentation:
            bits.append(element.documentation.replace('"""', "'''"))
        if call_args:
            attr_names = ", ".join(name for name, _, _ in call_args)
            bits.append(f"Args: {attr_names}.")
        return " ".join(bits)

    # ------------------------------------------------------------------
    # Naming
    # ------------------------------------------------------------------

    def _safe_method_name(self, tag: str) -> tuple[str, str | None]:
        """Return (method_name, alias_or_None).

        XSD tag names containing characters not allowed in Python
        identifiers, or colliding with Python keywords, are slugged.
        The original XSD tag is preserved via ``@element(tags=...)``.
        """
        identifier = re.sub(r"[^0-9a-zA-Z_]", "_", tag)
        if not identifier or not identifier[0].isalpha() and identifier[0] != "_":
            identifier = f"_{identifier}"
        if keyword.iskeyword(identifier):
            identifier = f"{identifier}_"
        if identifier == tag:
            return tag, None
        return identifier, tag

    # ------------------------------------------------------------------
    # Probes for imports
    # ------------------------------------------------------------------

    def _uses_regex(self, model: NamespaceModel) -> bool:
        for el in model.elements:
            for c, _ in self._iter_constraints(el):
                if c.pattern:
                    return True
        return False

    def _uses_range(self, model: NamespaceModel) -> bool:
        for el in model.elements:
            for c, _ in self._iter_constraints(el):
                if c.min_inclusive is not None or c.max_inclusive is not None:
                    return True
        return False

    def _uses_literal(self, model: NamespaceModel) -> bool:
        for el in model.elements:
            for c, _ in self._iter_constraints(el):
                if c.base == "enum" and c.enum_values:
                    return True
        return False

    def _uses_decimal(self, model: NamespaceModel) -> bool:
        for el in model.elements:
            for c, _ in self._iter_constraints(el):
                if c.base == "decimal":
                    return True
        return False


# ----------------------------------------------------------------------
# Module-level helpers (no instance state, simple text utilities)
# ----------------------------------------------------------------------

def _format_sub_tag(name: str, min_o: int, max_o: int | None) -> str:
    """Format a single ``sub_tags`` entry per ``_parse_sub_tags_spec`` syntax."""
    if min_o == 0 and max_o is None:
        return name
    if min_o == max_o:
        return f"{name}[{min_o}]"
    if max_o is None:
        return f"{name}[{min_o}:]"
    return f"{name}[{min_o}:{max_o}]"


def _safe_param_name(name: str) -> str:
    """Ensure ``name`` is a legal Python parameter."""
    identifier = re.sub(r"[^0-9a-zA-Z_]", "_", name)
    if identifier and identifier[0].isdigit():
        identifier = f"_{identifier}"
    if keyword.iskeyword(identifier):
        identifier = f"{identifier}_"
    return identifier or "_arg"


def _constraint_notes(constraint: SimpleConstraint, label: str) -> list[str]:
    """Return human-readable notes for constraints the grammar drops."""
    notes: list[str] = []
    if constraint.min_length is not None or constraint.max_length is not None:
        lo = constraint.min_length if constraint.min_length is not None else 0
        hi = constraint.max_length if constraint.max_length is not None else "*"
        notes.append(f"{label}: length [{lo}..{hi}] not emitted (grammar gap)")
    if constraint.total_digits is not None:
        notes.append(
            f"{label}: totalDigits={constraint.total_digits} not emitted (grammar gap)"
        )
    if constraint.fraction_digits is not None:
        notes.append(
            f"{label}: fractionDigits={constraint.fraction_digits} not emitted (grammar gap)"
        )
    return notes


if __name__ == "__main__":
    # Smoke-test on the in-tree FatturaPA XSD.
    import sys

    from .backend import XmlschemaBackend

    if len(sys.argv) != 3:
        print("Usage: python -m genro_builders.contrib.xsd.codegen.generator <schema.xsd> <ClassName>")
        sys.exit(1)
    model = XmlschemaBackend().load(sys.argv[1])
    source = PythonGenerator().render(model, sys.argv[2])
    print(source)
