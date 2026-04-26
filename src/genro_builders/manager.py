# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderManager and ReactiveManager — registry of builders.

A BuilderManager is a registry of builders. Each builder owns a
private ``local_store`` Bag (its own data area). The manager itself
holds no monolithic data store.

Cross-builder data access goes through volume syntax: a pointer
``^name:key`` resolves the volume part to ``manager.resolve_volume(name)``,
which returns the local_store of the builder registered under ``name``.

Pointer forms resolved by builders:
    - ``^key`` — reads from the builder's own local_store.
    - ``^.key`` — relative, reads via the datapath chain.
    - ``^other:key`` — reads from another builder's local_store (volume syntax).

Data infrastructure elements (``data_setter``, ``data_formula``)
are processed during the build phase. They write to the shared
reactive store and, when ``subscribe()`` is active, re-execute
automatically when their ^pointer dependencies change.
Formula execution follows topological order (dependencies first).

Lifecycle:
    1. ``__init__``: create builders via ``register_builder()``.
    2. ``setup()``: populate source (calls ``main()`` or ``main_<name>()``).
    3. ``build()``: materialize all builders (source -> built, two-pass:
       data elements first, then normal elements).
    4. render/compile: produce output.

For reactive bindings (formula re-execution, _delay, _interval), use
``ReactiveManager`` which adds ``subscribe()``.

Async-safe: ``build()`` and ``run()`` return None in sync context, or a
coroutine in async context.  Use ``smartawait`` for transparent handling::

    from genro_toolbox import smartawait

    # Sync — works as before:
    manager.run()

    # Async — await the coroutine:
    await smartawait(manager.run())

Example — single builder:
    >>> class SalesPage(HtmlManager):
    ...     def main(self, source):
    ...         self.local_store()['title'] = 'Hello'
    ...         source.h1(value='^title')
    ...
    >>> page = SalesPage()
    >>> print(page.render())

Example — multiple builders:
    >>> class InfraStack(BuilderManager):
    ...     def on_init(self):
    ...         self.compose = self.register_builder('compose', ComposeBuilder)
    ...         self.traefik = self.register_builder('traefik', TraefikBuilder)
    ...
    ...     def main_compose(self, source):
    ...         source.service(
    ...             image='^.image',                     # relative
    ...             domain='^traefik:domain',            # cross-builder
    ...         )
    ...
    ...     def main_traefik(self, source):
    ...         source.router(
    ...             rule='^domain',                      # own namespace
    ...             entrypoints='^.entrypoints',         # relative
    ...         )
    ...
    >>> stack = InfraStack()
    >>> stack.run()
    >>> print(stack.compose.render())
"""
from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from typing import Any

from genro_bag import Bag, BagNode
from genro_toolbox import is_async_context, smartawait

from .dependency_graph import DependencyGraph
from .render_target import RenderTarget


class BuilderManager:
    """Sync coordinator: a registry of builders, each with its own local_store.

    The manager holds a ``{name: builder._data}`` registry of per-builder
    local_store Bags. There is no monolithic shared store. Cross-builder
    data access goes through ``resolve_volume(name)``.

    Subclass lifecycle:
        ``on_init()``: Override to register builders via ``register_builder()``.

        ``main(source)`` or ``main_<name>(source)``: Override to populate
            each builder's source Bag.

        ``setup()``: Orchestrates main dispatch.

        ``build()``: Materializes all builders (source → built).

    For reactive bindings, use ``ReactiveManager`` instead.
    """

    __slots__ = ("_stores", "_builders", "_current_builder_name")

    def __init__(self) -> None:
        self._stores: dict[str, Bag] = {}
        self._builders: dict[str, Any] = {}
        self._current_builder_name: str | None = None
        self.on_init()

    def on_init(self) -> None:
        """Override to register builders via ``register_builder()``."""

    def register_builder(self, name: str, builder_class: type, **kwargs: Any) -> Any:
        """Create a builder and record it in the registry.

        The builder owns its private ``_data`` Bag. The manager records
        a reference to that Bag in ``self._stores`` so that
        ``resolve_volume(name)`` and ``local_store(name)`` can find it.

        Args:
            name: Name for the builder. Used for main dispatch
                (``main_<name>``) and as the volume identifier in
                cross-builder pointers (``^<name>:path``).
            builder_class: The BagBuilderBase subclass to instantiate.
            **kwargs: Extra kwargs passed to the builder constructor.

        Returns:
            The created builder instance.
        """
        builder = builder_class(manager=self, **kwargs)
        self._builders[name] = builder
        builder._builder_name = name

        store = builder._data
        if not store.backref:
            store.set_backref()
        self._stores[name] = store

        return builder

    def local_store(self, builder: str | None = None) -> Bag:
        """Return the private data Bag owned by a registered builder.

        Args:
            builder: Builder name. If None, uses the current builder
                context (set automatically during ``main()`` dispatch).

        Returns:
            The builder's private ``_data`` Bag.

        Raises:
            RuntimeError: If no builder context and no name given.
            KeyError: If the named builder is not registered.
        """
        name = builder if builder is not None else self._current_builder_name
        if name is None:
            raise RuntimeError(
                "local_store() called without a builder name and no "
                "current builder context (outside main dispatch)"
            )
        if name not in self._stores:
            raise KeyError(f"Builder '{name}' not registered")
        return self._stores[name]

    def resolve_volume(self, name: str) -> Bag:
        """Return the local_store Bag of a registered builder by volume name.

        Semantic alias of ``local_store(name)`` used during pointer
        resolution: ``^name:path`` resolves the volume part to this Bag.

        Raises:
            KeyError: If the named builder is not registered.
        """
        return self.local_store(name)

    def main(self, source: Any) -> None:
        """Populate the source of a single-builder manager. Override in subclass.

        Called by ``setup()`` when there is exactly one builder and
        no ``main_<name>`` method is defined.

        Args:
            source: The builder's source Bag to populate with elements.
        """

    def setup(self) -> None:
        """Populate source via main dispatch.

        For each builder named N calls ``main_N(source)``. If only one
        builder and no ``main_N`` exists, calls ``main(source)`` instead.

        Sets ``_current_builder_name`` during each main dispatch so that
        ``local_store()`` without arguments resolves correctly.
        """
        for name, builder in self._builders.items():
            self._current_builder_name = name
            main_method = getattr(self, f"main_{name}", None)
            if main_method is not None:
                main_method(builder.source)
            elif len(self._builders) == 1:
                self.main(builder.source)
        self._current_builder_name = None

    def build(self) -> Any:
        """Materialize all builders: source -> built.

        Returns None when all builders are synchronous, or a coroutine
        when any builder's build() returns an awaitable.
        """
        results = [builder.build() for builder in self._builders.values()]
        awaitables = [r for r in results if inspect.isawaitable(r)]
        if not awaitables:
            return None

        async def await_all():
            for coro in awaitables:
                await smartawait(coro)

        return await_all()

    def run(self) -> Any:
        """Setup and build -- single-call lifecycle.

        Returns None when all builders are synchronous, or a coroutine
        when any builder's build() returns an awaitable.
        In async case, caller must: ``await smartawait(manager.run())``.
        """
        self.setup()
        return self.build()


@dataclass
class _RenderTargetEntry:
    """Internal: a configured render target for a (builder, renderer) pair."""

    target: RenderTarget
    min_interval: float = 0
    last_render_time: float = field(default=0, repr=False)


class ReactiveManager(BuilderManager):
    """BuilderManager with reactive bindings and dependency graph.

    Adds ``subscribe()`` to activate reactive data binding on all
    registered builders. Maintains a cross-builder dependency graph
    that tracks how data paths affect builders (render/build).

    Reactive flow (async only):
        1. Data changes in the global store.
        2. The manager's subscriber collects changed paths.
        3. On next event loop tick (call_soon), the manager flushes:
           queries the dependency graph, determines impacted builders,
           and calls ``on_data_changed()`` with the results.

    Use this when your host environment provides an event loop
    (Textual, ASGI, Jupyter, asyncio.run).

    For one-shot sync pipelines, use BuilderManager directly.
    """

    __slots__ = (
        "_dep_graph",
        "_pending_changes",
        "_flush_scheduled",
        "_dispatching",
        "_subscribed",
        "_render_targets",
    )

    _SUBSCRIBER_ID = "reactive_manager"

    def __init__(self) -> None:
        self._dep_graph = DependencyGraph()
        self._pending_changes: list[str] = []
        self._flush_scheduled = False
        self._dispatching = False
        self._subscribed = False
        self._render_targets: dict[tuple[str, str], _RenderTargetEntry] = {}
        super().__init__()

    @property
    def dep_graph(self) -> DependencyGraph:
        """The cross-builder dependency graph (read-only access)."""
        return self._dep_graph

    def build(self) -> Any:
        """Materialize all builders and rebuild the dependency graph."""
        self._dep_graph.clear()
        return super().build()

    def subscribe(self) -> None:
        """Activate reactive bindings: subscribe to each builder's local_store.

        Also activates per-builder reactive bindings (incremental compile).
        Requires an async event loop for flush via call_soon.
        """
        if not self._subscribed:
            for name, store in self._stores.items():
                if not store.backref:
                    store.set_backref()
                store.subscribe(
                    self._SUBSCRIBER_ID,
                    any=self._make_store_callback(name),
                )
            self._subscribed = True

        for builder in self._builders.values():
            builder.subscribe()

    def unsubscribe(self) -> None:
        """Deactivate reactive bindings."""
        if self._subscribed:
            for store in self._stores.values():
                store.unsubscribe(self._SUBSCRIBER_ID, any=True)
            self._subscribed = False
        self._pending_changes.clear()
        self._flush_scheduled = False

    def _make_store_callback(self, builder_name: str) -> Any:
        """Build a per-builder subscribe callback that captures the name."""
        def callback(
            node: BagNode | None = None,
            pathlist: list | None = None,
            evt: str = "",
            **kwargs: Any,
        ) -> None:
            self._on_store_changed(
                builder_name=builder_name,
                node=node, pathlist=pathlist, evt=evt, **kwargs,
            )
        return callback

    # -----------------------------------------------------------------------
    # Render targets
    # -----------------------------------------------------------------------

    def set_render_target(
        self,
        builder_or_renderer: str,
        renderer_name: str | None = None,
        *,
        target: RenderTarget,
        min_interval: float = 0,
    ) -> None:
        """Configure a render target for a (builder, renderer) pair.

        When data changes impact the builder, the manager renders via
        the named renderer and writes the output to the target.

        For single-builder managers, the first argument is the renderer name.
        For multi-builder managers, pass (builder_name, renderer_name).

        Args:
            builder_or_renderer: Builder name (multi-builder) or renderer
                name (single-builder).
            renderer_name: Renderer name. Required for multi-builder.
            target: The RenderTarget to write output to.
            min_interval: Minimum seconds between renders (throttle).

        Example::

            # Single builder
            app.set_render_target("html",
                target=FileRenderTarget("index.html"), min_interval=5)

            # Multi builder
            app.set_render_target("page", "html",
                target=FileRenderTarget("page.html"), min_interval=5)
        """
        if renderer_name is None:
            if len(self._builders) == 1:
                builder_name = next(iter(self._builders))
                renderer_name = builder_or_renderer
            else:
                raise RuntimeError(
                    "Multiple builders registered — specify both "
                    "builder name and renderer name."
                )
        else:
            builder_name = builder_or_renderer

        if builder_name not in self._builders:
            raise KeyError(f"Builder '{builder_name}' not registered")

        key = (builder_name, renderer_name)
        self._render_targets[key] = _RenderTargetEntry(
            target=target, min_interval=min_interval,
        )

    # -----------------------------------------------------------------------
    # Data change handling
    # -----------------------------------------------------------------------

    def _on_store_changed(
        self,
        builder_name: str | None = None,
        node: BagNode | None = None,
        pathlist: list | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Callback from a builder's local_store subscribe — collect changed path.

        ``pathlist`` is local to the builder's store. The reconstructed
        path matches what ``abs_datapath`` registers in the dependency
        graph (no builder_name prefix).
        """
        if self._dispatching or pathlist is None:
            return

        parts = [str(p) for p in pathlist]
        if evt in ("ins", "del") and node is not None:
            parts.append(node.label)
        changed_path = ".".join(parts)

        self._pending_changes.append(changed_path)

        if not self._flush_scheduled:
            self._flush_scheduled = True
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon(self._flush)
            except RuntimeError:
                # No event loop — sync context. Flush immediately.
                self._flush()

    def _flush(self) -> None:
        """Process pending data changes: query graph, dispatch actions."""
        self._flush_scheduled = False

        changes = self._pending_changes
        self._pending_changes = []
        if not changes:
            return

        self._dispatching = True
        try:
            impacted = self._dep_graph.impacted_builders(changes)
            if impacted:
                self.on_data_changed(impacted)
        finally:
            self._dispatching = False

    def on_data_changed(self, impacted: dict[str, str]) -> None:
        """Called when data changes affect builders. Renders to configured targets.

        For each impacted builder that has render targets configured via
        ``set_render_target()``, renders via the named renderer and writes
        to the target. Respects ``min_interval`` throttling.

        If dep_type is 'build', rebuilds the builder first (full rebuild).

        Override for custom behavior (framework-specific updates, etc.).

        Args:
            impacted: Dict mapping builder name to max dependency type
                ('render' or 'build').
        """
        now = time.monotonic()

        for builder_name, dep_type in impacted.items():
            builder = self._builders.get(builder_name)
            if builder is None:
                continue

            if dep_type == "build":
                builder.build()

            # Render to all configured targets for this builder
            for (b_name, r_name), entry in self._render_targets.items():
                if b_name != builder_name:
                    continue
                if entry.min_interval > 0:
                    elapsed = now - entry.last_render_time
                    if elapsed < entry.min_interval:
                        continue
                output = builder.render(name=r_name)
                entry.target.write(output)
                entry.last_render_time = now

    def run(self, *, subscribe: bool = False) -> Any:
        """Setup, build, and activate reactive wiring -- single-call lifecycle.

        Auto-activation: if render targets are registered and we are in an
        async context, reactive subscription and the initial render happen
        automatically. Explicit ``subscribe=True`` forces subscription even
        without render targets or in sync context.

        Returns None when all builders are synchronous, or a coroutine
        when any builder's build() returns an awaitable.

        Args:
            subscribe: If True, force reactive bindings regardless of
                render targets or async context.
        """
        self.setup()
        build_result = self.build()

        def activate() -> None:
            auto = bool(self._render_targets) and is_async_context()
            if subscribe or auto:
                self.subscribe()
            if self._render_targets:
                self._render_all_targets()

        if inspect.isawaitable(build_result):
            async def cont():
                await smartawait(build_result)
                activate()

            return cont()

        activate()
        return None

    def _render_all_targets(self) -> None:
        """Render every registered target once. Used for initial render."""
        now = time.monotonic()
        for (b_name, r_name), entry in self._render_targets.items():
            builder = self._builders.get(b_name)
            if builder is None:
                continue
            entry.target.write(builder.render(name=r_name))
            entry.last_render_time = now
