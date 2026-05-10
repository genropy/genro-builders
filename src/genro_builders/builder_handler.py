# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderHandler — engine that drives a single Builder (decisions 4, 5, 9).

The handler owns:
    - one ``builder`` instance (decision 9: monobuilder per istanza);
    - the ``source`` and ``built`` bags (decisions 4 and 12, level 2);
    - the ``_node_index`` mapping ``node_id -> path`` (decision 11);
    - the ``render_target`` slot (decision 6).

Lifecycle (decision 5):
    handler = MyHandler()
    handler.create()    # main(source) -> populate self.source
    handler.build()     # builder.build(source, built) -> self.built
    handler.render()    # builder.render(mode, render_target=...)

Subclasses (typically ``HtmlBuilderHandler``, etc.) set
``builder_class`` and override ``main(self, root)``.
"""
from __future__ import annotations

from typing import Any

from .builder_bag import BuilderBagNode
from .built_bag import BuilderBuiltBag, BuilderSourceBag


class BuilderHandler:
    """Engine that drives one builder through the create/build/render lifecycle."""

    builder_class: type | None = None

    def __init__(self) -> None:
        if self.builder_class is None:
            raise TypeError(
                f"{type(self).__name__} must declare a builder_class "
                "(decision 9: handler subclasses bind a specific builder).",
            )
        self.builder = self.builder_class()
        self.source = BuilderSourceBag(builder=self.builder, handler=self)
        self.built = BuilderBuiltBag(builder=self.builder, handler=self)
        self._node_index: dict[str, str] = {}
        self._render_target: Any = None

    # ------------------------------------------------------------------
    # Lifecycle (decision 5)
    # ------------------------------------------------------------------

    def create(self) -> None:
        """Populate the source bag by invoking ``main(self.source)``."""
        self.main(self.source)

    def build(self) -> None:
        """Materialize ``self.source`` into ``self.built`` via the builder."""
        self.builder.build(self.source, self.built)

    def render(self, mode: str | None = None) -> Any:
        """Serialize ``self.built`` via the builder, honoring render_target."""
        return self.builder.render(
            self.built, mode=mode, render_target=self._render_target,
        )

    # ------------------------------------------------------------------
    # Render target (decision 6)
    # ------------------------------------------------------------------

    @property
    def render_target(self) -> Any:
        return self._render_target

    @render_target.setter
    def render_target(self, value: Any) -> None:
        self._render_target = value

    # ------------------------------------------------------------------
    # node_id index (decision 11)
    # ------------------------------------------------------------------

    def register_node_id(self, node_id: str, path: str) -> None:
        """Record ``node_id -> path``. Raise on collision."""
        existing = self._node_index.get(node_id)
        if existing is not None and existing != path:
            raise ValueError(
                f"Duplicate node_id '{node_id}': already mapped to '{existing}', "
                f"cannot remap to '{path}'.",
            )
        self._node_index[node_id] = path

    def node_by_id(self, node_id: str, stage: str = "built") -> BuilderBagNode:
        """Return the node registered under ``node_id`` from source or built."""
        if stage not in ("source", "built"):
            raise ValueError(
                f"stage must be 'source' or 'built', got {stage!r}",
            )
        path = self._node_index[node_id]
        bag = getattr(self, stage)
        return bag.get_node(path)

    # ------------------------------------------------------------------
    # User hook
    # ------------------------------------------------------------------

    def main(self, root: BuilderSourceBag) -> None:
        """Override in subclass to populate the source bag."""
        raise NotImplementedError(
            f"{type(self).__name__}.main(root) must be implemented by the subclass",
        )
