# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XmlschemaBackend — map an ``xmlschema.XMLSchema`` to a NamespaceModel.

Lazy import of ``xmlschema``: the optional dependency is touched only
inside :meth:`XmlschemaBackend.load`, so importing this module without
``xmlschema`` installed does not raise. The error surfaces with a
clear actionable message when the user actually invokes the codegen.

The backend collects:
- global elements and every element appearing inside complex types
  (recursively; names already seen are skipped with a warning),
- attributes with their use / type,
- simple-content constraints (text payload of a complex type),
- facets translated into :class:`~.model.SimpleConstraint` fields.

Out of scope in this release (warnings only):
- ``xs:import``: namespaces beyond the target are reported but their
  elements are not introspected. ``NamespaceModel.imports`` is
  populated as reference for a future multi-namespace codegen.
- ``xs:include``: not yet exercised by FatturaPA but xmlschema merges
  them transparently at load time, so the backend sees a unified
  schema either way.
- ``substitutionGroup``, ``xs:any``, ``xsi:type`` discriminators.
"""

from __future__ import annotations

import sys
import warnings
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .model import (
    AttributeModel,
    ChildModel,
    ElementModel,
    NamespaceModel,
    NamespaceRef,
    SimpleConstraint,
)

if TYPE_CHECKING:
    # Imported only by type checkers, never at runtime.
    pass


XSD_NS = "http://www.w3.org/2001/XMLSchema"


class XsdCodegenWarning(UserWarning):
    """Emitted by :class:`XmlschemaBackend` when an XSD construct is
    accepted but only partially modelled (e.g. a namespace import is
    recorded as a reference but not introspected)."""


class XmlschemaBackend:
    """Parser-backend for the codegen pipeline, based on ``xmlschema``.

    Construction is cheap (no IO). ``load`` performs the parse and
    returns a :class:`NamespaceModel`.
    """

    def load(self, xsd_path: str | Path) -> NamespaceModel:
        """Parse ``xsd_path`` and return the intermediate model.

        Raises:
            ImportError: if ``xmlschema`` is not installed. The message
                hints at ``pip install 'genro-builders[xsd]'``.
        """
        try:
            import xmlschema  # noqa: PLC0415
        except ImportError as err:
            raise ImportError(
                "XSD codegen requires the 'xmlschema' package. "
                "Install with: pip install 'genro-builders[xsd]'"
            ) from err

        schema = xmlschema.XMLSchema(str(xsd_path))
        model = NamespaceModel(target_namespace=schema.target_namespace)

        for uri, sub in schema.imports.items():
            if sub is None:
                # xmlschema records unresolved imports as None.
                model.imports.append(NamespaceRef(uri=uri))
                continue
            model.imports.append(NamespaceRef(uri=sub.target_namespace or uri))
            warnings.warn(
                f"namespace import {sub.target_namespace!r} is recorded but "
                "not introspected; elements declared there will not appear "
                "in the generated builder (multi-namespace codegen is future work).",
                XsdCodegenWarning,
                stacklevel=2,
            )

        # Walk: global elements first, then recurse into complex types.
        seen: set[str] = set()
        for el in schema.elements.values():
            self._collect_element(el, model, seen)

        return model

    # ------------------------------------------------------------------
    # Element collection
    # ------------------------------------------------------------------

    def _collect_element(
        self,
        xsd_element: Any,
        model: NamespaceModel,
        seen: set[str],
    ) -> None:
        """Add ``xsd_element`` (and any locally-defined children) to
        ``model``. Names already present in ``seen`` are skipped with a
        warning — a single grammar cannot have two definitions for the
        same tag, so the first wins."""
        name = xsd_element.local_name
        if name is None:
            return
        if name in seen:
            warnings.warn(
                f"element {name!r} declared multiple times; only the first "
                "definition is kept in the generated builder.",
                XsdCodegenWarning,
                stacklevel=2,
            )
            return
        seen.add(name)

        element = ElementModel(name=name)
        if xsd_element.annotation is not None:
            doc = str(xsd_element.annotation).strip()
            if doc:
                element.documentation = doc

        xsd_type = xsd_element.type
        if xsd_type is None:
            model.elements.append(element)
            return

        if xsd_type.is_simple():
            element.text_constraint = self._extract_simple_constraint(xsd_type)
            model.elements.append(element)
            return

        # Complex type.
        for attr_name, xsd_attr in xsd_type.attributes.items():
            if attr_name is None:
                continue
            element.attrs.append(self._build_attribute(attr_name, xsd_attr))

        # simpleContent? xmlschema exposes it as has_simple_content().
        if xsd_type.has_simple_content():
            base_type = xsd_type.base_type
            if base_type is not None and base_type.is_simple():
                element.text_constraint = self._extract_simple_constraint(base_type)

        # Iterate child elements (collapses sequence/choice/all into a flat list).
        content = getattr(xsd_type, "content", None)
        if content is not None and hasattr(content, "iter_elements"):
            for child in content.iter_elements():
                child_name = child.local_name
                if child_name is None:
                    continue
                element.children.append(
                    ChildModel(
                        name=child_name,
                        min_occurs=child.min_occurs or 0,
                        max_occurs=child.max_occurs,
                    )
                )

        model.elements.append(element)

        # Recurse into locally-defined children so they too get their own
        # @element entry.
        if content is not None and hasattr(content, "iter_elements"):
            for child in content.iter_elements():
                self._collect_element(child, model, seen)

    # ------------------------------------------------------------------
    # Attributes and simple constraints
    # ------------------------------------------------------------------

    def _build_attribute(self, name: str, xsd_attr: Any) -> AttributeModel:
        constraint: SimpleConstraint | None = None
        if xsd_attr.type is not None and xsd_attr.type.is_simple():
            constraint = self._extract_simple_constraint(xsd_attr.type)
        return AttributeModel(
            name=name,
            required=(getattr(xsd_attr, "use", "optional") == "required"),
            constraint=constraint,
        )

    def _extract_simple_constraint(self, xsd_simple: Any) -> SimpleConstraint:
        """Translate a :class:`xmlschema` simple type into a constraint.

        The mapping intentionally loses some XSD precision: e.g. ``xs:date``
        becomes ``"string"`` because the builder grammar has no
        date validator. Future grammar extensions can re-read the raw
        facets from the model.
        """
        primitive = getattr(xsd_simple, "primitive_type", None)
        primitive_name = ""
        if primitive is not None and getattr(primitive, "local_name", None):
            primitive_name = primitive.local_name
        base = _xsd_builtin_to_base(primitive_name)

        enum = getattr(xsd_simple, "enumeration", None)
        if enum:
            return SimpleConstraint(base="enum", enum_values=list(enum))

        constraint = SimpleConstraint(base=base)

        for facet_qname, facet in xsd_simple.facets.items():
            if facet_qname is None:
                # Anonymous restriction without a named facet; nothing to map.
                continue
            local = facet_qname.split("}")[-1] if "}" in facet_qname else facet_qname
            value = getattr(facet, "value", None)
            if local == "pattern":
                regexps = getattr(facet, "regexps", None)
                if regexps:
                    constraint.pattern = regexps[0]
            elif local == "minLength" and value is not None:
                constraint.min_length = int(value)
            elif local == "maxLength" and value is not None:
                constraint.max_length = int(value)
            elif local == "length" and value is not None:
                constraint.min_length = int(value)
                constraint.max_length = int(value)
            elif local == "minInclusive" and value is not None:
                constraint.min_inclusive = _as_decimal(value)
            elif local == "maxInclusive" and value is not None:
                constraint.max_inclusive = _as_decimal(value)
            elif local == "totalDigits" and value is not None:
                constraint.total_digits = int(value)
            elif local == "fractionDigits" and value is not None:
                constraint.fraction_digits = int(value)

        return constraint


_BUILTIN_BASE_MAP = {
    "string": "string",
    "normalizedString": "string",
    "token": "string",
    "anyURI": "string",
    "date": "string",
    "dateTime": "string",
    "time": "string",
    "gYearMonth": "string",
    "gYear": "string",
    "integer": "int",
    "int": "int",
    "long": "int",
    "short": "int",
    "byte": "int",
    "positiveInteger": "int",
    "nonNegativeInteger": "int",
    "decimal": "decimal",
    "double": "decimal",
    "float": "decimal",
    "boolean": "bool",
}


def _xsd_builtin_to_base(name: str) -> str:
    """Map an XSD primitive type name to the abstract category the
    generator understands (``string``/``int``/``decimal``/``bool``)."""
    return _BUILTIN_BASE_MAP.get(name, "string")


def _as_decimal(value: Any) -> Decimal | None:
    """Best-effort numeric coercion.

    XSD ``minInclusive``/``maxInclusive`` can carry non-numeric values
    (e.g. ``Date10`` for ``xs:date`` types). Those are silently skipped
    here: the builder grammar has no date validator anyway, and the
    raw value is preserved in the XSD itself which remains the source
    of truth for full conformance checking.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m genro_builders.contrib.xsd.codegen.backend <schema.xsd>")
        sys.exit(1)
    backend = XmlschemaBackend()
    model = backend.load(sys.argv[1])
    print(f"targetNamespace = {model.target_namespace}")
    print(f"#imports = {len(model.imports)}")
    print(f"#elements = {len(model.elements)}")
    for el in model.elements[:5]:
        print(
            f"  {el.name}: "
            f"#children={len(el.children)}, "
            f"#attrs={len(el.attrs)}, "
            f"text={el.text_constraint}"
        )
