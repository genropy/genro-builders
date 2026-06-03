# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSD codegen package.

Three-layer pipeline that turns an XSD schema into a self-contained
Python module:

    XSD file
      -> XmlschemaBackend.load (lazy import of xmlschema)
      -> NamespaceModel  (parser-neutral intermediate model)
      -> PythonGenerator.render
      -> Python source text  (committed in the repo, e.g. sitemap.py)

The generated module declares a ``<Dialect>Builder(XsdBuilderBase)`` +
``<Dialect>Handler(XsdHandler)`` pair — no hand-written glue. The user
subclasses the handler and implements ``main`` (see
``contrib/xsd/examples/sitemap/`` and ``examples/fatturapa/``).

The codegen produces a *starting base*, not a guaranteed-complete dialect.
The intermediate model records XSD constraints the grammar does not yet
emit (``totalDigits``, ``minLength``), and XSD patterns Python's ``re``
cannot compile (Unicode block properties such as ``\\p{IsBasicLatin}``)
are surfaced as ``# NOTE:`` comments for hand-refinement — never silently
dropped, never emitted as code that would raise at validation time.

Optional dependency: ``xmlschema`` (installed via the ``[xsd]`` extra)
is required only by the backend at codegen time. Consumers of a
generated module do **not** need it.
"""

from __future__ import annotations

from .backend import XmlschemaBackend
from .generator import PythonGenerator
from .model import (
    AttributeModel,
    ChildModel,
    ElementModel,
    NamespaceModel,
    NamespaceRef,
    SimpleConstraint,
)

__all__ = [
    "AttributeModel",
    "ChildModel",
    "ElementModel",
    "NamespaceModel",
    "NamespaceRef",
    "PythonGenerator",
    "SimpleConstraint",
    "XmlschemaBackend",
]
