# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSD codegen package.

Three-layer pipeline that turns an XSD schema into a static Python
builder module:

    XSD file
      -> XmlschemaBackend.load (lazy import of xmlschema)
      -> NamespaceModel  (parser-neutral intermediate model)
      -> PythonGenerator.render
      -> Python source text  (committed in the repo as e.g. fatturapa_elements.py)

The committed Python module is then imported by a hand-written
``Builder`` subclass that pairs it with renderers and a handler preset
(see ``contrib/xsd/examples/fatturapa/`` for the reference example).

The intermediate model intentionally records XSD constraints that the
builder grammar does not yet emit as validators (e.g. ``totalDigits``,
``minLength``). They live on the model so a future grammar extension
can pick them up without touching the backend.

Optional dependency: ``xmlschema`` (installed via the ``[xsd]`` extra)
is required only by the backend at codegen time. Consumers of a
generated module (e.g. ``FatturaPABuilder``) do **not** need it.
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
