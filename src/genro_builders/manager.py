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
    2. ``store(store)``: populate shared data at the store root.
    3. ``main_<name>(source)``: populate each builder's source.
    4. ``build()``: orchestrate the full pipeline.

Example — single builder:
    >>> class MyPage(BuilderManager):
    ...     def __init__(self):
    ...         self.page = self.set_builder('page', HtmlBuilder)
    ...
    ...     def store(self, store):
    ...         store['title'] = 'Hello'
    ...
    ...     def main(self, source):
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
    ...     def store(self, store):
    ...         store['domain'] = 'example.com'
    ...         store['env'] = 'production'
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

        ``store(store)``: Override to set shared data values
            at the store root. Called once during ``build()``.

        ``main(source)`` (single builder) or
        ``main_<name>(source)`` (multiple builders):
            Override to define each builder's source. Receives:
                - source: the builder's source Bag to populate.

        ``build()``: Runs the full pipeline —
            store → main → build_all.

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

    def store(self, store: Bag) -> None:
        """Populate shared data at the store root. Override in subclass.

        Called once during ``build()``, before main methods.
        Values set here are accessible to all builders via absolute
        ``^pointer`` paths (e.g., ``^domain``).

        Args:
            store: The reactive store root Bag.
        """

    def main(self, source: Any) -> None:
        """Populate the source of a single-builder manager. Override in subclass.

        Called during ``build()`` when there is exactly one builder and
        no ``main_<name>`` method is defined.

        Args:
            source: The builder's source Bag to populate with elements.
        """

    def build(self) -> None:
        """Run the full pipeline: store → main → build_all.

        1. Calls ``store(reactive_store)`` to populate shared data.
        2. For each builder named N, calls ``main_N(source)``
           where source is the builder's source Bag.
           If only one builder and no ``main_N`` exists, calls
           ``main(source)`` instead.
        3. Materializes all builders via ``build_all()``.
        """
        reactive_store = self.reactive_store
        self.store(reactive_store)

        for name, builder in self._builders.items():
            main_method = getattr(self, f"main_{name}", None)
            if main_method is not None:
                main_method(builder.source)
            elif len(self._builders) == 1:
                self.main(builder.source)

        self.build_all()

    def build_all(self) -> None:
        """Build all registered builders (without calling hooks)."""
        for builder in self._builders.values():
            builder.build()
