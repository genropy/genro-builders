# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Output mixin: render, compile, schema access, validation.

Handles output methods: ``render()`` / ``compile()`` dispatch to named
renderer/compiler instances, ``_check()`` / ``_walk_check()`` validation
report, ``_schema_to_md()`` documentation generation, and schema
introspection (``__contains__``, ``_get_schema_info``, ``__iter__``,
``__repr__``, ``__str__``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from genro_bag import Bag

from ._utilities import _parse_parent_tags_spec, _parse_sub_tags_spec

if TYPE_CHECKING:
    from genro_bag import BagNode


class _OutputMixin:
    """Mixin for render, compile, schema access, documentation, and value rendering."""

    # -----------------------------------------------------------------------
    # Render / compile dispatch
    # -----------------------------------------------------------------------

    def render(
        self, built_bag: Bag | None = None, name: str | None = None,
        output: Any = None,
    ) -> str:
        """Render the built Bag to output string.

        Args:
            built_bag: The built Bag to render. Defaults to self.built.
            name: Renderer name. If None and only one renderer, uses that.
            output: Optional destination (file path, stream, etc.).
                Interpretation depends on the renderer implementation.

        Returns:
            Rendered output string.
        """
        if built_bag is None:
            built_bag = self.built
        instance = self._get_output("renderer", self._renderer_instances, name)
        if instance is not None:
            return instance.render(built_bag, output=output)
        raise RuntimeError(
            f"{type(self).__name__} has no renderer registered."
        )

    def compile(
        self, built_bag: Bag | None = None, name: str | None = None,
        target: Any = None,
    ) -> Any:
        """Compile the built Bag into live objects.

        Args:
            built_bag: The built Bag to compile. Defaults to self.built.
            name: Compiler name. If None and only one compiler, uses that.
            target: Optional target (parent widget, container, etc.).
                Interpretation depends on the compiler implementation.

        Returns:
            Compiled output (type depends on compiler).
        """
        if built_bag is None:
            built_bag = self.built
        instance = self._get_output("compiler", self._compiler_instances, name)
        if instance is not None:
            return instance.compile(built_bag, target=target)
        raise RuntimeError(
            f"{type(self).__name__} has no compiler registered."
        )

    def add_renderer(self, name: str, renderer_class: type) -> None:
        """Register a renderer instance at runtime."""
        self._renderer_instances[name] = renderer_class(self)

    def add_compiler(self, name: str, compiler_class: type) -> None:
        """Register a compiler instance at runtime."""
        self._compiler_instances[name] = compiler_class(self)

    # -----------------------------------------------------------------------
    # Schema access
    # -----------------------------------------------------------------------

    def __contains__(self, name: str) -> bool:
        """Check if element exists in schema."""
        return self._schema.get_node(name) is not None

    def _get_schema_info(self, name: str) -> dict:
        """Return info dict for a schema element.

        The result is a dict of all schema-node attributes, extended with
        computed keys. Common keys (presence depends on element type):

            sub_tags, sub_tags_compiled, parent_tags, parent_tags_compiled,
            call_args_validations, _meta, documentation,
            handler_name, is_component, is_data_element,
            component_builder, based_on, slots.

        Results are cached on the schema node after first access.

        Raises KeyError if element not in schema.
        """
        schema_node = self._schema.get_node(name)
        if schema_node is None:
            raise KeyError(f"Element '{name}' not found in schema")

        cached = schema_node.attr.get("_cached_info")  # type: ignore[union-attr]
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        result = dict(schema_node.attr)  # type: ignore[union-attr]
        inherits_from = result.pop("inherits_from", None)

        if inherits_from:
            # Support multiple inheritance: "alfa,beta" -> ["alfa", "beta"]
            # Parents are processed left-to-right, later parents override earlier ones
            parents = [p.strip() for p in inherits_from.split(",")]
            for parent in parents:
                abstract_attrs = self._schema.get_attr(parent)
                if abstract_attrs:
                    for k, v in abstract_attrs.items():
                        # Skip inherits_from from abstract - don't propagate it
                        if k == "inherits_from":
                            continue
                        if k == "_meta":
                            # Merge meta: abstract base + element overrides
                            inherited = v or {}
                            current = result.get("_meta") or {}
                            result["_meta"] = {**inherited, **current}
                        elif k not in result or not result[k]:
                            result[k] = v

        sub_tags = result.get("sub_tags")
        if sub_tags is not None:
            result["sub_tags_compiled"] = _parse_sub_tags_spec(sub_tags)

        parent_tags = result.get("parent_tags")
        if parent_tags is not None:
            result["parent_tags_compiled"] = _parse_parent_tags_spec(parent_tags)

        schema_node.attr["_cached_info"] = result  # type: ignore[union-attr]
        return result

    def __iter__(self):
        """Iterate over schema nodes."""
        return iter(self._schema)

    def __repr__(self) -> str:
        """Show builder schema summary."""
        count = sum(1 for _ in self)
        return f"<{type(self).__name__} ({count} elements)>"

    def __str__(self) -> str:
        """Show schema structure."""
        return str(self._schema)

    # -----------------------------------------------------------------------
    # Validation check
    # -----------------------------------------------------------------------

    def _check(self, bag: Bag | None = None) -> list[tuple[str, BagNode, list[str]]]:
        """Return report of invalid nodes."""
        if bag is None:
            bag = self._bag
        invalid_nodes: list[tuple[str, BagNode, list[str]]] = []
        self._walk_check(bag, "", invalid_nodes)
        return invalid_nodes

    def validate(self, bag: Bag | None = None) -> list[dict[str, Any]]:
        """Validate the bag structure, returning a list of validation errors.

        Walks the bag tree and checks every node against its schema
        constraints (sub_tags, cardinality, parent_tags).

        Args:
            bag: The Bag to validate. Defaults to the builder's source bag.

        Returns:
            List of error dicts, each with keys:
                - ``path``: dot-separated path to the invalid node
                - ``tag``: the node's tag name
                - ``reasons``: list of human-readable reason strings

            Empty list means the structure is valid.
        """
        raw = self._check(bag)
        return [
            {"path": path, "tag": node.node_tag or node.label, "reasons": reasons}
            for path, node, reasons in raw
        ]

    def _walk_check(
        self,
        bag: Bag,
        path: str,
        invalid_nodes: list[tuple[str, BagNode, list[str]]],
    ) -> None:
        """Walk tree collecting invalid nodes."""
        for node in bag:
            node_path = f"{path}.{node.label}" if path else node.label

            if node._invalid_reasons:
                invalid_nodes.append((node_path, node, node._invalid_reasons.copy()))

            node_value = node.get_value(static=True)
            if isinstance(node_value, Bag):
                self._walk_check(node_value, node_path, invalid_nodes)

    def _schema_to_md(self, title: str | None = None) -> str:
        """Generate Markdown documentation for the builder schema.

        Creates a formatted Markdown document with tables for abstract
        and concrete elements, including all schema information.

        Args:
            title: Optional title for the document. Defaults to class name.

        Returns:
            Markdown string with schema documentation.
        """
        from ..contrib.markdown import MarkdownBuilder

        md_builder = MarkdownBuilder()
        doc = md_builder.source
        builder_name = title or type(self).__name__

        doc.h1(f"Schema: {builder_name}")

        # Collect abstracts and elements
        abstracts: list[tuple[str, dict]] = []
        elements: list[tuple[str, dict]] = []

        for node in self._schema:
            name = node.label
            info = self._get_schema_info(name)
            if name.startswith("@"):
                abstracts.append((name[1:], info))
            else:
                elements.append((name, info))

        # Abstract elements section
        if abstracts:
            doc.h2("Abstract Elements")
            table = doc.table()
            header = table.tr()
            header.th("Name")
            header.th("Sub Tags")
            header.th("Documentation")

            for name, info in sorted(abstracts):
                row = table.tr()
                row.td(f"`@{name}`")
                row.td(f"`{info.get('sub_tags') or '-'}`")
                row.td(info.get("documentation") or "-")

        # Concrete elements section
        if elements:
            doc.h2("Elements")
            table = doc.table()
            header = table.tr()
            header.th("Name")
            header.th("Inherits")
            header.th("Sub Tags")
            header.th("Call Args")
            header.th("Compile")
            header.th("Documentation")

            for name, info in sorted(elements):
                row = table.tr()
                row.td(f"`{name}`")

                inherits = info.get("inherits_from")
                row.td(f"`{inherits}`" if inherits else "-")

                sub_tags = info.get("sub_tags")
                row.td(f"`{sub_tags}`" if sub_tags else "-")

                call_args = info.get("call_args_validations")
                if call_args:
                    args_str = ", ".join(call_args.keys())
                    row.td(f"`{args_str}`")
                else:
                    row.td("-")

                meta = info.get("_meta") or {}
                meta_parts = []
                if "template" in meta:
                    tmpl = meta["template"].replace("`", "\\`")
                    tmpl = tmpl.replace("\n", "\\n")
                    meta_parts.append(f"template: {tmpl}")
                if "callback" in meta:
                    meta_parts.append(f"callback: {meta['callback']}")
                for k, v in meta.items():
                    if k not in ("template", "callback"):
                        meta_parts.append(f"{k}: {v}")
                if meta_parts:
                    row.td("`" + ", ".join(meta_parts) + "`")
                else:
                    row.td("-")

                row.td(info.get("documentation") or "-")

        md_builder.build()
        return md_builder.render()
