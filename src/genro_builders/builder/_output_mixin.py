# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Output mixin: render, compile, validation.

Handles output methods: ``render()`` / ``compile()`` dispatch to named
renderer/compiler instances, and ``_check()`` / ``validate()`` /
``_walk_check()`` validation report.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from genro_bag import Bag

if TYPE_CHECKING:
    from genro_bag import BagNode


class _OutputMixin:
    """Mixin for render, compile, and validation."""

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
