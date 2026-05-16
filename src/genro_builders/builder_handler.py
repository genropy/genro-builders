# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderHandler — engine that drives a single Builder (decisions 4, 5, 9).

The handler owns:
    - one ``builder`` instance (decision 4: handler manages its builder);
    - the ``source`` bag (decisions 4 and 12);
    - the ``_node_index`` mapping ``node_id -> path`` (decision 11);
    - the dict ``mode -> target`` of render targets (decision 6).

Lifecycle (decision 5):
    handler = MyHandler()
    handler.create()    # main(source) -> populate self.source
    handler.render()    # dispatch to the renderer bound to the
                        # default mode, using its registered target.

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
        self._render_targets: dict[str, Any] = {}
        self._default_render_mode: str | None = None
        self._renderer_cache: dict[str, Any] = {}
        self._subbuilder_cache: dict[str, Any] = {}
        self._sub_renderer_cache: dict[int, Any] = {}

    def _get_renderer(self, mode: str) -> Any:
        """Return the (cached) renderer instance for ``mode``."""
        if mode not in self._renderer_cache:
            renderer_cls = self.builder._renderers[mode]
            self._renderer_cache[mode] = renderer_cls(self)
        return self._renderer_cache[mode]

    # ------------------------------------------------------------------
    # Lifecycle (decision 5)
    # ------------------------------------------------------------------

    def create(self) -> None:
        """Populate the source bag by invoking ``main(self.source)``."""
        self.main(self.source)

    def render(
        self,
        target: Any = None,
        mode: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Render the source via the renderer bound to ``mode``.

        Argument ``target`` semantics (decision 6 v0.4.0):

        - ``False`` → forces return-as-string, ignores any registered
          target for the chosen mode;
        - any other falsy value (``None``, ``""``, ``0``) → falls back
          to the target registered under ``mode`` (see
          ``set_render_target``);
        - truthy value → used directly as the target for this call.

        ``mode`` resolution:

        - explicit ``mode`` argument wins;
        - otherwise the handler's ``_default_render_mode`` (set via
          ``set_render_target(..., default=True)``);
        - otherwise the builder's ``_default_render_mode``.

        The renderer corresponding to ``mode`` is looked up in the
        builder's ``_renderers`` registry and instantiated on the fly.
        """
        effective_mode = (
            mode
            or self._default_render_mode
            or self.builder._default_render_mode
        )
        effective_target = (
            None if target is False
            else target or self._render_targets.get(effective_mode)
        )
        renderer = self._get_renderer(effective_mode)
        return renderer.render(
            self.source,
            mode=effective_mode,
            render_target=effective_target,
            **kwargs,
        )

    def set_render_target(
        self,
        mode: str,
        target: Any,
        default: bool = False,
    ) -> None:
        """Register a render target for ``mode``.

        Overrides any previous registration under the same mode. When
        ``default=True`` the mode also becomes the handler's default
        for plain ``self.render()`` calls.
        """
        self._render_targets[mode] = target
        if default:
            self._default_render_mode = mode

    def __getattr__(self, name: str) -> Any:
        """Auto-generated ``render_<mode>`` shortcuts.

        ``handler.render_xml('out.xml')`` is equivalent to
        ``handler.render(target='out.xml', mode='xml')``. The shortcut
        is generated only when the mode exists in the builder's
        renderer registry; otherwise the lookup falls through to the
        normal ``AttributeError``.
        """
        if name.startswith("render_"):
            mode = name[len("render_"):]
            registry = getattr(self.builder, "_renderers", None)
            if registry is not None and mode in registry:
                def shortcut(target: Any = None, **kwargs: Any) -> Any:
                    return self.render(target=target, mode=mode, **kwargs)
                return shortcut
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}",
        )

    # ------------------------------------------------------------------
    # Renderer property (decision 8)
    # ------------------------------------------------------------------

    @property
    def renderer(self) -> Any:
        """Lazy, cached dialect renderer for the dialect's default mode.

        Available for inspection (``handler.renderer._STYLE_ROOTS``,
        etc.) or for explicit calls when the shortcut
        ``handler.render(...)`` is too narrow.
        """
        return self._get_renderer(self.builder._default_render_mode)

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
        renderer class is read from the sub-builder's renderer registry
        (default mode) and instantiated once per handler. The
        sub-renderer carries an explicit ``builder`` reference so
        polymorphic dispatch via ``node._builder`` can identify it
        correctly.
        """
        if builder is self.builder:
            return self.renderer
        key = id(builder)
        if key not in self._sub_renderer_cache:
            mode = builder._default_render_mode
            renderer_cls = builder._renderers[mode]
            self._sub_renderer_cache[key] = renderer_cls(self, builder)
        return self._sub_renderer_cache[key]

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
