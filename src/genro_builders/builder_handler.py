# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderHandler — engine that drives a single Builder (decisions 4, 5, 9).

The handler owns:
    - one ``builder`` instance (decision 4: handler manages its builder);
    - the ``source`` bag (decisions 4 and 12);
    - the ``_node_index`` mapping ``node_id -> path`` (decision 11);
    - the ``render_target`` slot (decision 6).

Lifecycle (decision 5):
    handler = MyHandler()
    handler.create()    # main(source) -> populate self.source
    handler.render()    # builder.render(mode, render_target=...)

Subclasses (typically ``HtmlBuilderHandler``, etc.) set
``builder_class`` and override ``main(self, root)``.
"""
from __future__ import annotations

from typing import Any

from .builder import BagBuilderBase
from .builder_bag import BuilderBagNode
from .source_bag import BuilderSource


class BuilderHandler:
    """Engine that drives one builder through the create/render lifecycle."""

    builder_class: type | None = None

    def __init__(self) -> None:
        if self.builder_class is None:
            raise TypeError(
                f"{type(self).__name__} must declare a builder_class "
                "(decision 9: handler subclasses bind a specific builder).",
            )
        self.builder = self.builder_class()
        self.source = BuilderSource(builder=self.builder, handler=self)
        self._node_index: dict[str, str] = {}
        self._render_target: Any = None
        self._renderer: Any = None
        self._subbuilder_cache: dict[str, Any] = {}
        self._sub_renderer_cache: dict[int, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle (decision 5)
    # ------------------------------------------------------------------

    def create(self) -> None:
        """Populate the source bag by invoking ``main(self.source)``."""
        self.main(self.source)

    def render(self, mode: str | None = None, **kwargs: Any) -> Any:
        """Shortcut to ``self.renderer.render(...)``.

        Forwards to the dialect's renderer (lazy property, see
        ``self.renderer``) with ``render_target`` already populated
        from ``self._render_target``. Extra ``**kwargs`` are
        mode-specific options filtered downstream against the target
        ``render_<mode>`` signature. See decision 6 and decision 8.
        """
        return self.renderer.render(
            self.source, mode=mode, render_target=self._render_target,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Renderer (decision 8)
    # ------------------------------------------------------------------

    @property
    def renderer(self) -> Any:
        """Lazy, cached dialect renderer.

        Instantiated from ``builder._renderer_class`` on first access.
        Available for inspection (``handler.renderer._STYLE_ROOTS``,
        etc.) or for explicit calls when the shortcut
        ``handler.render(...)`` is too narrow.
        """
        if self._renderer is None:
            self._renderer = self.builder._renderer_class(self)
        return self._renderer

    # ------------------------------------------------------------------
    # Sub-builder cache (decision 2)
    # ------------------------------------------------------------------

    def get_subbuilder(self, name: str) -> Any:
        """Return a cached sub-builder instance by canonical name.

        Looks up the class in the global registry via
        :meth:`BagBuilderBase.get_builder_class` and instantiates it
        once per handler. Subsequent calls with the same name return
        the same instance (sub-builders are essentially stateless
        grammars, so one instance per dialect per document is enough).
        """
        if name not in self._subbuilder_cache:
            cls = BagBuilderBase.get_builder_class(name)
            self._subbuilder_cache[name] = cls()
        return self._subbuilder_cache[name]

    def renderer_for(self, builder: Any) -> Any:
        """Return the (cached) renderer instance bound to ``builder``.

        For the primary builder this is just ``self.renderer``. For a
        sub-builder (a different dialect attached to a subtree), the
        renderer class is read from the sub-builder's ``_renderer_class``
        and instantiated once per handler. The sub-renderer carries
        an explicit ``builder`` reference so polymorphic dispatch via
        ``node._builder`` can identify it correctly.
        """
        if builder is self.builder:
            return self.renderer
        key = id(builder)
        if key not in self._sub_renderer_cache:
            self._sub_renderer_cache[key] = builder._renderer_class(self, builder)
        return self._sub_renderer_cache[key]

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

    def node_by_id(self, node_id: str) -> BuilderBagNode:
        """Return the source node registered under ``node_id``."""
        path = self._node_index[node_id]
        return self.source.get_node(path)

    # ------------------------------------------------------------------
    # User hook
    # ------------------------------------------------------------------

    def main(self, root: BuilderSource) -> None:
        """Override in subclass to populate the source bag."""
        raise NotImplementedError(
            f"{type(self).__name__}.main(root) must be implemented by the subclass",
        )
