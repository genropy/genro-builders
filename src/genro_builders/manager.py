# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderManager and ReactiveManager — coordinate builders with shared data.

A BuilderManager coordinates one or more builders that share a common
reactive data store. Each builder gets a private data namespace under
``reactive_store['builders.<name>']``, while shared data lives at the
store root.

The reactive store is a Bag with ^pointer support. Builders resolve
pointers against it:
    - ``^key`` — absolute, reads from the store root (shared data).
    - ``^.key`` — relative, reads from the builder's private namespace.

Data infrastructure elements (``data_setter``, ``data_formula``,
``data_controller``) are processed during the build phase. They write
to the shared reactive store and, when ``subscribe()`` is active,
re-execute automatically when their ^pointer dependencies change.
Formula execution follows topological order (dependencies first).

Lifecycle:
    1. ``__init__``: create builders via ``register_builder()``.
    2. ``setup()``: populate data and source (calls ``store()`` then ``main()``).
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

Example — single builder (HtmlBuilder provides renderers):
    >>> class HtmlManager(BuilderManager):
    ...     def __init__(self):
    ...         self.page = self.register_builder('page', HtmlBuilder)
    ...
    ...     def render(self):
    ...         return self.page.render()

    >>> class SalesPage(HtmlManager):
    ...     def __init__(self):
    ...         super().__init__()
    ...         self.setup()
    ...         self.build()
    ...
    ...     def store(self, data):
    ...         data['title'] = 'Hello'
    ...
    ...     def main(self, source):
    ...         source.h1(value='^title')
    ...
    >>> page = SalesPage()
    >>> print(page.render())

Example — multiple builders with shared and private data:
    >>> class InfraStack(BuilderManager):
    ...     def __init__(self):
    ...         self.compose = self.register_builder('compose', ComposeBuilder)
    ...         self.traefik = self.register_builder('traefik', TraefikBuilder)
    ...
    ...     def store(self, data):
    ...         data['domain'] = 'example.com'
    ...         data['env'] = 'production'
    ...
    ...     def main_compose(self, source):
    ...         source.service(
    ...             image='^.image',                     # private (relative)
    ...             domain='^domain',                    # shared (absolute)
    ...         )
    ...
    ...     def main_traefik(self, source):
    ...         source.router(
    ...             rule='^domain',                      # shared
    ...             entrypoints='^.entrypoints',         # private
    ...         )
    ...
    >>> stack = InfraStack()
    >>> stack.run()
    >>> print(stack.compose.render())
"""
from __future__ import annotations

import inspect
from typing import Any

from genro_bag import Bag
from genro_toolbox import smartawait


class BuilderManager:
    """Sync coordinator for one or more builders with a shared data store.

    The reactive store is a Bag that holds both shared data (at root level)
    and per-builder private data (under ``builders.<name>``).

    Subclass lifecycle:
        ``on_init()``: Override to register builders via ``register_builder()``.

        ``store(data)``: Override to populate shared data at the store root.

        ``main(source)`` or ``main_<name>(source)``: Override to populate
            each builder's source Bag.

        ``setup()``: Orchestrates store → main.

        ``build()``: Materializes all builders (source → built).

    For reactive bindings, use ``ReactiveManager`` instead.
    """

    __slots__ = ("_data", "_builders")

    def __init__(self) -> None:
        self._data = Bag()
        self._data.set_backref()
        self._builders: dict[str, Any] = {}
        self.on_init()

    def on_init(self) -> None:
        """Override to register builders via ``register_builder()``."""

    @property
    def reactive_store(self) -> Bag:
        """The shared reactive data store.

        Holds shared data at root level and per-builder private data
        under ``builders.<name>``. Builders resolve ``^pointer`` paths
        against this store.
        """
        return self._data

    @reactive_store.setter
    def reactive_store(self, value: Bag | dict[str, Any]) -> None:
        """Replace the reactive store. Rebinds all registered builders."""
        new_data = Bag(source=value) if isinstance(value, dict) else value
        if not new_data.backref:
            new_data.set_backref()
        self._data = new_data
        for builder in self._builders.values():
            builder._rebind_data(new_data)

    def register_builder(self, name: str, builder_class: type, **kwargs: Any) -> Any:
        """Create a builder, register it, and set up its private data namespace.

        Creates the builder, registers it in the builder registry, and
        creates a private data namespace at ``reactive_store['builders.<name>']``.
        Sets the ``datapath`` attribute on the builder's source root so that
        relative ``^.pointer`` paths resolve to the private namespace.

        Args:
            name: Name for the builder. Used for main dispatch
                (``main_<name>``) and data namespace (``builders.<name>``).
            builder_class: The BagBuilderBase subclass to instantiate.
            **kwargs: Extra kwargs passed to the builder constructor.

        Returns:
            The created builder instance.
        """
        builder = builder_class(manager=self, **kwargs)
        self._builders[name] = builder

        # Create private data namespace
        builders_bag = self._data.get_item("builders")
        if builders_bag is None or not isinstance(builders_bag, Bag):
            self._data.set_item("builders", Bag())
            builders_bag = self._data.get_item("builders")
        builders_bag.set_item(name, Bag())

        # Set datapath on source root for relative ^.pointer resolution
        root_node = builder._source_shell.get_node("root")
        if root_node is not None:
            root_node.set_attr({"datapath": f"builders.{name}"})

        return builder

    def store(self, data: Bag) -> None:
        """Populate shared data at the store root. Override in subclass.

        Called by ``setup()`` before main methods.
        Values set here are accessible to all builders via absolute
        ``^pointer`` paths (e.g., ``^domain``).

        Args:
            data: The reactive store root Bag.
        """

    def main(self, source: Any) -> None:
        """Populate the source of a single-builder manager. Override in subclass.

        Called by ``setup()`` when there is exactly one builder and
        no ``main_<name>`` method is defined.

        Args:
            source: The builder's source Bag to populate with elements.
        """

    def setup(self) -> None:
        """Populate data and source: store → main.

        Calls ``store(reactive_store)`` to populate shared data, then
        for each builder named N calls ``main_N(source)``. If only one
        builder and no ``main_N`` exists, calls ``main(source)`` instead.
        """
        self.store(self.reactive_store)

        for name, builder in self._builders.items():
            main_method = getattr(self, f"main_{name}", None)
            if main_method is not None:
                main_method(builder.source)
            elif len(self._builders) == 1:
                self.main(builder.source)

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


class ReactiveManager(BuilderManager):
    """BuilderManager with reactive bindings support.

    Adds ``subscribe()`` to activate reactive data binding on all
    registered builders. Use this when your host environment provides
    an event loop (Textual, ASGI, Jupyter, asyncio.run).

    For one-shot sync pipelines, use BuilderManager directly.
    """

    def subscribe(self) -> None:
        """Activate reactive bindings on all builders."""
        for builder in self._builders.values():
            builder.subscribe()

    def run(self, *, subscribe: bool = False) -> Any:
        """Setup, build, and optionally subscribe -- single-call lifecycle.

        Returns None when all builders are synchronous, or a coroutine
        when any builder's build() returns an awaitable.

        Args:
            subscribe: If True, also activate reactive bindings after build.
        """
        self.setup()
        build_result = self.build()

        if inspect.isawaitable(build_result):
            async def cont():
                await smartawait(build_result)
                if subscribe:
                    self.subscribe()

            return cont()

        if subscribe:
            self.subscribe()
        return None
