# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Output mixin: render, compile, schema access, documentation, value rendering.

Handles all output-producing methods: ``render()`` / ``compile()`` dispatch
to named renderer/compiler instances, ``_compile()`` legacy fallback,
``_schema_to_md()`` documentation generation, ``_render_value()`` template
transformations, ``_check()`` / ``_walk_check()`` validation report, and
schema introspection (``__contains__``, ``_get_schema_info``, ``__iter__``,
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
        # Legacy fallback: _compiler_instance
        if self._compiler_instance is not None:
            if hasattr(self._compiler_instance, "render"):
                return self._compiler_instance.render(built_bag)
            parts = list(self._compiler_instance._walk_compile(built_bag))
            return "\n\n".join(p for p in parts if p)
        raise RuntimeError(
            f"{type(self).__name__} has no renderer or compiler for rendering."
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
        """Return info dict for an element.

        Returns dict with keys:
            - adapter_name: str | None
            - sub_tags: str | None
            - sub_tags_compiled: dict[str, tuple[int, int]] | None
            - call_args_validations: dict | None

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

    # -----------------------------------------------------------------------
    # Compiler access (legacy)
    # -----------------------------------------------------------------------

    @property
    def _compiler(self) -> Any:
        """Return compiler instance for this builder.

        Requires _compiler_class to be defined on the builder subclass.

        Raises:
            ValueError: If _compiler_class is not defined.
        """
        if self._compiler_class is None:
            raise ValueError(f"{type(self).__name__} has no _compiler_class defined")
        return self._compiler_class(self)

    def _compile(self, **kwargs: Any) -> Any:
        """Compile the bag via the compiler, then render to output string.

        If _compiler_class is defined, compiles source into a target bag
        and then renders it using the compiler's render method.

        Without _compiler_class, falls back to XML/JSON serialization (string).

        Args:
            **kwargs: Extra parameters. 'destination' writes output to file.
                'format' selects legacy format ('xml' or 'json').

        Returns:
            Rendered output string.
        """
        if self._compiler_class is not None:
            from ..binding import BindingManager
            from ..builder_bag import BuilderBag

            compiler = self._compiler
            target = BuilderBag(builder=type(self))
            data = kwargs.pop("data", None) or Bag()
            binding = kwargs.pop("binding", None) or BindingManager()
            self._build_walk(self._bag, target, data, binding)

            destination = kwargs.get("destination")
            if hasattr(compiler, "render"):
                result = compiler.render(target)
            else:
                parts = list(compiler._walk_compile(target))
                result = "\n".join(p for p in parts if p)

            if destination is not None:
                from pathlib import Path
                Path(destination).write_text(result)

            return result
        format_ = kwargs.get("format", "xml")
        if format_ == "xml":
            return self._bag.to_xml()
        elif format_ == "json":
            return self._bag.to_tytx(transport="json")  # type: ignore[return-value]
        else:
            raise ValueError(f"Unknown format: {format_}")

    # -----------------------------------------------------------------------
    # Schema documentation
    # -----------------------------------------------------------------------

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

    # -----------------------------------------------------------------------
    # Value rendering (for compile)
    # -----------------------------------------------------------------------

    def _render_value(self, node: BagNode) -> str:
        """Render node value applying format and template transformations.

        Applies transformations in order:
        1. value_format (node attr) - format the raw value
        2. value_template (node attr) - apply runtime template
        3. _meta callback - call method to modify context in place
        4. _meta format - format from decorator
        5. _meta template - structural template from decorator

        Template placeholders available:
        - {node_value}: the node value
        - {node_label}: the node label
        - {attr_name}: any node attribute (e.g., {lang}, {href})

        Args:
            node: The BagNode to render.

        Returns:
            Rendered string value.
        """
        node_value = node.get_value(static=True)
        node_value = "" if node_value is None else str(node_value)

        # Build template context: node_value, node_label, and all attributes
        # Start with default values from schema for optional parameters
        tag = node.node_tag or node.label
        info = self._get_schema_info(tag)
        call_args = info.get("call_args_validations") or {}
        template_ctx: dict[str, Any] = {}
        for param_name, (default, _validators, _type) in call_args.items():
            if default is not None:
                template_ctx[param_name] = default
        # Override with actual node attributes
        template_ctx.update(node.attr)
        template_ctx["node_value"] = node_value
        template_ctx["node_label"] = node.label
        template_ctx["_node"] = node  # For callbacks needing full node access

        # 1. value_format from node attr (runtime)
        value_format = node.attr.get("value_format")
        if value_format:
            try:
                node_value = value_format.format(node_value)
                template_ctx["node_value"] = node_value
            except (ValueError, KeyError):
                pass

        # 2. value_template from node attr (runtime)
        value_template = node.attr.get("value_template")
        if value_template:
            node_value = value_template.format(**template_ctx)
            template_ctx["node_value"] = node_value

        # 3-5. _meta callback, format, template from schema
        meta = info.get("_meta") or {}

        # 3. callback - call method to modify context in place
        callback = meta.get("callback")
        if callback:
            method = getattr(self, callback)
            method(template_ctx)
            node_value = template_ctx["node_value"]

        # 4. format from _meta
        fmt = meta.get("format")
        if fmt:
            try:
                node_value = fmt.format(node_value)
                template_ctx["node_value"] = node_value
            except (ValueError, KeyError):
                pass

        # 5. template from _meta
        template = meta.get("template")
        if template:
            node_value = template.format(**template_ctx)

        return node_value

    # -----------------------------------------------------------------------
    # Call args validation (internal)
    # -----------------------------------------------------------------------

    def _get_call_args_validations(self, tag: str) -> dict[str, tuple[Any, list, Any]] | None:
        """Return attribute spec for a tag from schema."""
        schema_node = self._schema.node(tag)
        if schema_node is None:
            return None
        return schema_node.attr.get("call_args_validations")
