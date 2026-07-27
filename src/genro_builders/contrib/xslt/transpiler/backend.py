# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Phase-1 XSLT->Python transpiler: lxml tree walk -> Python AST.

``XsltTranspiler.transpile(xslt_source)`` parses the stylesheet with
lxml, walks it, and builds a Python ``ast.Module`` that, when run with
:class:`XsltBuilder`, rebuilds the same stylesheet. ``ast.unparse``
turns the module into source text.

Translation rules (phase 1):

- An element in the XSLT namespace (``{...XSL/Transform}for-each``) maps
  to the builder method whose ``render_tag`` is ``xslt:<local>``
  (discovered from the schema, so the prefix in the source — ``xsl`` or
  any other — is irrelevant; only the URI matters). ``output``/
  ``template`` map to ``xslt_output``/``xslt_template``.
- Any other element is a literal result element: the method is its
  local name, sanitised for Python (``del`` -> ``del_``).
- Attributes become keyword arguments. ``class``/``for`` (Python
  keywords as HTML attributes) become ``class_``/``for_``; the XSLT
  namespace declaration ``xmlns:<p>`` becomes ``xmlns_<p>``; everything
  else (``select``, ``match``, ``test``, ``name``, ``href``, ...) passes
  through verbatim. ``{...}`` attribute-value-templates are plain string
  values — the transpiler does not interpret them.
- An element with only text (no child elements) passes the text as a
  single positional argument: ``<th>URL</th>`` -> ``th("URL")``.
- An element with child elements gets a variable; each child is built on
  it. One variable per such element (phase 1 keeps it flat and verbose).
"""

from __future__ import annotations

import ast
import keyword
from typing import Any

from lxml import etree

from ..xslt_builder import XsltBuilder

#: The one namespace URI that marks an XSLT instruction. Recognised by
#: URI, never by prefix (a stylesheet may bind it to any prefix).
_XSLT_URI = "http://www.w3.org/1999/XSL/Transform"

#: HTML attribute names that collide with Python keywords; the builder
#: exposes them with a trailing underscore (the canonical PEP 8 form
#: resolved in SourceBagNode.runtime_values).
_ATTR_KEYWORD_MAP = {"class": "class_", "for": "for_"}


class XsltTranspiler:
    """Transpile an XSLT stylesheet to Python source rebuilding it.

    ``handler_name`` is the class name of the generated builder; the
    generated module subclasses ``XsltBuilder`` and writes the stylesheet
    in ``main``. The generated class creates and renders itself.
    """

    def __init__(self, handler_name: str = "GeneratedStylesheet"):
        self.handler_name = handler_name
        self._instruction_methods = self._discover_instruction_methods()
        self._root_var = "root"

    def _discover_instruction_methods(self) -> dict[str, str]:
        """Map XSLT local-name -> builder method, read from the schema.

        Each instruction declares ``_meta['render_tag'] = 'xslt:<local>'``;
        invert that so ``for-each`` -> ``for_each`` is discovered, not
        hard-coded. Keeps the transpiler in step with the grammar.
        """
        builder = XsltBuilder()
        mapping: dict[str, str] = {}
        for node in builder._schema:
            tag = node.label
            if tag.startswith("_"):
                continue
            render_tag = (builder._get_schema_info(tag).get("_meta") or {}).get("render_tag")
            if render_tag and render_tag.startswith("xslt:"):
                local = render_tag[len("xslt:"):]
                mapping[local] = tag
        return mapping

    def transpile(self, xslt_source: str | bytes) -> str:
        """Return Python source that rebuilds ``xslt_source``."""
        module = self._build_module(xslt_source)
        ast.fix_missing_locations(module)
        return ast.unparse(module)

    def _build_module(self, xslt_source: str | bytes) -> ast.Module:
        if isinstance(xslt_source, str):
            xslt_source = xslt_source.encode("utf-8")
        tree = etree.fromstring(xslt_source)

        body_statements: list[ast.stmt] = []
        self._var_counter = 0
        # The XML root element (``<stylesheet>``) is itself built on the
        # ``root`` bag, then its subtree on it — so treat it as a child of
        # ``root``, not as a container whose children we splice into root.
        self._emit_child(tree, parent_var=self._root_var, statements=body_statements)

        main_def = ast.FunctionDef(
            name="main",
            args=self._args("self", self._root_var),
            body=body_statements or [ast.Pass()],
            decorator_list=[],
        )
        class_def = ast.ClassDef(
            name=self.handler_name,
            bases=[ast.Name(id="XsltBuilder", ctx=ast.Load())],
            keywords=[],
            body=[main_def],
            decorator_list=[],
        )
        import_stmt = ast.ImportFrom(
            module="genro_builders.contrib.xslt",
            names=[ast.alias(name="XsltBuilder", asname=None)],
            level=0,
        )
        return ast.Module(body=[import_stmt, class_def], type_ignores=[])

    def _emit_element(
        self, element: Any, target_var: str, statements: list[ast.stmt]
    ) -> None:
        """Emit the children of ``element`` as builder calls on ``target_var``.

        ``element`` is the XML node whose builder call already produced
        ``target_var``; here we walk its element children and, for each,
        emit ``target_var.<method>(...)`` — recursing with a fresh
        variable when the child itself has element children.
        """
        for child in element:
            if not isinstance(child.tag, str):
                continue  # comments / processing instructions: skip
            self._emit_child(child, parent_var=target_var, statements=statements)

    def _emit_child(
        self, child: Any, parent_var: str, statements: list[ast.stmt]
    ) -> None:
        method = self._method_for(child)
        call = self._call_for(child, parent_var, method)

        grandchildren = [c for c in child if isinstance(c.tag, str)]
        if grandchildren:
            var = self._new_var(method)
            statements.append(
                ast.Assign(
                    targets=[ast.Name(id=var, ctx=ast.Store())],
                    value=call,
                )
            )
            self._emit_element(child, target_var=var, statements=statements)
        else:
            statements.append(ast.Expr(value=call))

    def _call_for(self, element: Any, parent_var: str, method: str) -> ast.Call:
        """Build ``parent_var.<method>(<text?>, **attrs)`` for ``element``."""
        args: list[ast.expr] = []
        text = (element.text or "").strip()
        if text:
            args.append(ast.Constant(value=text))
        keywords = [
            ast.keyword(arg=name, value=ast.Constant(value=value))
            for name, value in self._keyword_attrs(element)
        ]
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=parent_var, ctx=ast.Load()),
                attr=method,
                ctx=ast.Load(),
            ),
            args=args,
            keywords=keywords,
        )

    def _method_for(self, element: Any) -> str:
        """The builder method name for ``element`` (instruction or literal)."""
        qname = etree.QName(element.tag)
        local = qname.localname
        if qname.namespace == _XSLT_URI:
            try:
                return self._instruction_methods[local]
            except KeyError as err:
                raise ValueError(
                    f"unsupported XSLT instruction 'xslt:{local}'"
                ) from err
        return self._sanitize(local)

    def _keyword_attrs(self, element: Any) -> list[tuple[str, str]]:
        """Element attributes (and namespace decls) as (kwarg_name, value)."""
        pairs: list[tuple[str, str]] = []
        # Namespace declarations: emit as xmlns_<prefix> so the builder
        # surfaces xmlns:<prefix>. lxml's nsmap is cumulative (every node
        # reports the namespaces in scope), so emit only those a node
        # *introduces* — present here, absent on the parent.
        parent = element.getparent()
        parent_nsmap = parent.nsmap if parent is not None else {}
        for prefix, uri in (element.nsmap or {}).items():
            if not prefix or parent_nsmap.get(prefix) == uri:
                continue
            # The builder emits XSLT tags with its own fixed prefix
            # (``xslt``), regardless of the prefix the source bound to the
            # XSLT URI (``xsl``, ``mario``, ...). So declare the XSLT
            # namespace as ``xmlns_xslt``, not the source prefix — else the
            # emitted ``xslt:*`` tags reference an undeclared prefix. Other
            # namespaces (e.g. ``b``) keep their source prefix verbatim.
            out_prefix = "xslt" if uri == _XSLT_URI else prefix
            pairs.append((f"xmlns_{out_prefix}", uri))
        for name, value in element.attrib.items():
            qname = etree.QName(name)
            local = qname.localname
            kwarg = _ATTR_KEYWORD_MAP.get(local, self._sanitize_attr(local))
            pairs.append((kwarg, value))
        return pairs

    def _sanitize(self, local: str) -> str:
        """Local element name -> Python method name (``del`` -> ``del_``)."""
        name = local.replace("-", "_")
        if keyword.iskeyword(name):
            name += "_"
        return name

    def _sanitize_attr(self, local: str) -> str:
        """Attribute local name -> kwarg name (hyphens to underscores)."""
        return local.replace("-", "_")

    def _new_var(self, method: str) -> str:
        """A unique variable name based on the method (phase-1 naming)."""
        self._var_counter += 1
        return f"{method}_{self._var_counter}"

    def _args(self, *names: str) -> ast.arguments:
        return ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=n) for n in names],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )
