# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Build pipeline (decision 5, 8 — re-read 2026-05-08).

The build phase materializes the source bag (the user's recipe, with
``@component`` nodes left opaque) into the built bag. The pipeline is
**framework-level**: the same walk runs for every dialect. Concrete
builders are not expected to override ``build`` — they grow features
by adding behavior to the hooks (``_pre_build_node`` /
``_post_build_node``).

The default body is a 1:1 mirror. ``@component`` is dormant: when the
walk encounters a node tagged as a component, it raises
``NotImplementedError`` with a message that cites the restart and the
relevant decisions.
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag


class _BuildMixin:
    """Build pipeline. Lives on ``BagBuilderBase``, identical for all dialects."""

    def build(self, source: Bag, built: Bag) -> None:
        """Materialize ``source`` into ``built``.

        Iterates source nodes, calls ``_pre_build_node`` on each (which
        may transform or suppress the node), copies the resulting
        ``(label, value, attrs, node_tag)`` tuple into ``built``, then
        recurses on sub-bags so the structure mirrors the source.
        """
        self._mirror_bag(source, built)

    def _mirror_bag(self, src_bag: Bag, dst_bag: Bag) -> None:
        for src_node in src_bag:
            spec = self._pre_build_node(src_node)
            if spec is None:
                continue
            dst_node = self._copy_node(spec, dst_bag)
            self._post_build_node(spec, dst_node)
            # @subbuilder: a sub-dialect owns this subtree (decision 7,
            # generalised 2026-05-12). Hand the recursion off to the
            # sub-builder via its own ``build`` (default delegation), or
            # the body the dialect declared on the decorator.
            sub_builder = getattr(src_node, "_builder", None)
            if sub_builder is not None and sub_builder is not self:
                self._dispatch_subbuilder(src_node, dst_node, sub_builder)
                continue
            value = spec.value
            if isinstance(value, Bag):
                self._mirror_bag(value, dst_node.value)

    def _dispatch_subbuilder(
        self, src_node: Any, dst_node: Any, sub_builder: Any,
    ) -> None:
        """Expand a @subbuilder node by delegating to the sub-dialect.

        The destination node inherits the sub-builder so descendants
        keep the right grammar in built. The host body decorator can
        be customised (the framework reads ``handler_name`` and invokes
        the method when present); an empty body falls through to the
        default delegation ``sub_builder.build(source_value,
        dst_value)``.
        """
        # Mirror the sub-builder onto the built node so grammar lookups
        # on the built side continue to use it.
        dst_node._builder = sub_builder
        dst_node._handler = getattr(src_node, "_handler", None)
        # Recurse into the sub-bag via the sub-builder's own build.
        src_value = src_node.value
        if isinstance(src_value, Bag):
            sub_builder.build(src_value, dst_node.value)

    # ------------------------------------------------------------------
    # Hooks (override-able by future infrastructure, not by single dialects)
    # ------------------------------------------------------------------

    def _pre_build_node(self, src_node: Any) -> Any:
        """Hook called before copying a source node.

        Return the node spec to be copied, or ``None`` to drop it.
        Default: identity, with a guard that refuses ``@component``
        nodes (component expansion lands in a future phase, see
        decision 7).
        """
        info = self._schema_info_for(src_node)
        if info is not None and info.get("is_component"):
            raise NotImplementedError(
                f"@component '{src_node.node_tag or src_node.label}' "
                "encountered during build: component expansion is dormant "
                "during the 2026-05 restart (decision 7). The source "
                "preserves the recipe; future build phases will expand "
                "components into their inner elements.",
            )
        return src_node

    def _post_build_node(self, spec: Any, dst_node: Any) -> None:
        """Hook called after a node is copied. Default: no-op."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _copy_node(self, spec: Any, dst_bag: Bag) -> Any:
        """Copy a single source node into ``dst_bag``.

        Container values (sub-bags) become a fresh bag of the same
        class as the destination (the level-2 ``BuilderBuiltBag``),
        which the recursion then fills.
        """
        value = spec.value
        if isinstance(value, Bag):
            value = type(dst_bag)()
        attrs = dict(spec.attr)
        node_tag = attrs.pop("_tag", None) or spec.node_tag
        return Bag.set_item(
            dst_bag,
            spec.label,
            value,
            _attributes=attrs,
            node_tag=node_tag,
        )

    def _schema_info_for(self, src_node: Any) -> dict | None:
        """Return the schema entry for a node tag, or ``None`` if unknown."""
        tag = src_node.node_tag
        if not tag:
            return None
        try:
            return self._get_schema_info(tag)
        except (KeyError, AttributeError):
            return None
