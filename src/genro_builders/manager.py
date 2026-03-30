# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderManager — mixin to coordinate builders with a shared reactive store.

A BuilderManager coordinates one or more builders that share a common
reactive data store. Each builder gets a private data namespace under
``reactive_store['builders.<name>']``, while shared data lives at the
store root.

The reactive store is a Bag with ^pointer support. Builders resolve
pointers against it:
    - ``^key`` — absolute, reads from the store root (shared data).
    - ``^.key`` — relative, reads from the builder's private namespace.

Lifecycle:
    1. ``__init__``: create builders via ``set_builder()``.
    2. ``common_data(store)``: populate shared data at the store root.
    3. ``recipe_<name>(source, common, data)``: populate each builder's
       source template and private data.
    4. ``build()``: orchestrate the full pipeline.

Example — single builder:
    >>> class MyPage(BuilderManager):
    ...     def __init__(self):
    ...         self.page = self.set_builder('page', HtmlBuilder)
    ...
    ...     def common_data(self, store):
    ...         store['title'] = 'Hello'
    ...
    ...     def recipe(self, source, common, data):
    ...         source.h1(value='^title')
    ...
    >>> page = MyPage()
    >>> page.build()

Example — multiple builders with shared and private data:
    >>> class InfraStack(BuilderManager):
    ...     def __init__(self):
    ...         self.compose = self.set_builder('compose', ComposeBuilder)
    ...         self.traefik = self.set_builder('traefik', TraefikBuilder)
    ...
    ...     def common_data(self, store):
    ...         store['domain'] = 'example.com'
    ...         store['env'] = 'production'
    ...
    ...     def recipe_compose(self, source, common, data):
    ...         data['image'] = 'myapp:latest'          # builders.compose.image
    ...         data['replicas'] = 3                     # builders.compose.replicas
    ...         source.service(
    ...             image='^.image',                     # private (relative)
    ...             domain='^domain',                    # shared (absolute)
    ...         )
    ...
    ...     def recipe_traefik(self, source, common, data):
    ...         data['entrypoints'] = 'websecure'       # builders.traefik.entrypoints
    ...         source.router(
    ...             rule='^domain',                      # shared
    ...             entrypoints='^.entrypoints',         # private
    ...         )
    ...
    >>> stack = InfraStack()
    >>> stack.build()
    >>> # Change shared data — propagates to all builders
    >>> stack.reactive_store['domain'] = 'newapp.example.com'
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag


class BuilderManager:
    """Mixin to coordinate one or more builders with a shared reactive store.

    The reactive store is a Bag that holds both shared data (at root level)
    and per-builder private data (under ``builders.<name>``).

    Subclass lifecycle:
        ``__init__``: Create builders via ``set_builder(name, class)``.
            Each call registers the builder and creates its private
            namespace at ``reactive_store['builders.<name>']``.

        ``common_data(store)``: Override to set shared data values
            at the store root. Called once during ``build()``.

        ``recipe(source, common, data)`` (single builder) or
        ``recipe_<name>(source, common, data)`` (multiple builders):
            Override to define each builder's template. Receives:
                - source: the builder's source Bag to populate.
                - common: the store root (shared data, read/write).
                - data: the builder's private namespace Bag (read/write).

        ``build()``: Runs the full pipeline —
            common_data → recipes → build_all.

    Subclasses get ``_data`` and ``_builders`` initialized automatically
    via ``__init_subclass__`` — no ``super().__init__()`` needed.
    """

    __slots__ = ("_data", "_builders")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        original_init = cls.__dict__.get("__init__")
        if original_init is None:
            return

        def _wrapped_init(self: Any, *args: Any, **kw: Any) -> None:
            if not hasattr(self, "_data"):
                self._data = Bag()
                self._data.set_backref()
                self._builders: dict[str, Any] = {}
            original_init(self, *args, **kw)

        cls.__init__ = _wrapped_init  # type: ignore[attr-defined]

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

    def set_builder(self, name: str, builder_class: type, **kwargs: Any) -> Any:
        """Create a builder, register it, and set up its private data namespace.

        Creates the builder, registers it in the builder registry, and
        creates a private data namespace at ``reactive_store['builders.<name>']``.
        Sets the ``datapath`` attribute on the builder's source root so that
        relative ``^.pointer`` paths resolve to the private namespace.

        Args:
            name: Name for the builder. Used for recipe dispatch
                (``recipe_<name>``) and data namespace (``builders.<name>``).
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

    def common_data(self, store: Bag) -> None:
        """Populate shared data at the store root. Override in subclass.

        Called once during ``build()``, before recipes.
        Values set here are accessible to all builders via absolute
        ``^pointer`` paths (e.g., ``^domain``).

        Args:
            store: The reactive store root Bag.
        """

    def recipe(self, source: Any, common: Bag, data: Bag) -> None:
        """Populate the source of a single-builder manager. Override in subclass.

        Called during ``build()`` when there is exactly one builder and
        no ``recipe_<name>`` method is defined.

        Args:
            source: The builder's source Bag to populate with elements.
            common: The reactive store root (shared data).
            data: The builder's private data namespace.
        """

    def build(self) -> None:
        """Run the full pipeline: common_data → recipes → build_all.

        1. Calls ``common_data(reactive_store)`` to populate shared data.
        2. For each builder named N, calls ``recipe_N(source, common, data)``
           where common is the store root and data is ``reactive_store['builders.N']``.
           If only one builder and no ``recipe_N`` exists, calls
           ``recipe(source, common, data)`` instead.
        3. Materializes all builders via ``build_all()``.
        """
        store = self.reactive_store
        self.common_data(store)

        for name, builder in self._builders.items():
            builder_data = store.get_item(f"builders.{name}")
            recipe_method = getattr(self, f"recipe_{name}", None)
            if recipe_method is not None:
                recipe_method(builder.source, store, builder_data)
            elif len(self._builders) == 1:
                self.recipe(builder.source, store, builder_data)

        self.build_all()

    def build_all(self) -> None:
        """Build all registered builders (without calling hooks)."""
        for builder in self._builders.values():
            builder.build()
