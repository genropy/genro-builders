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

Data infrastructure elements (``data_setter``, ``data_formula``,
``data_controller``) are processed during the build phase. They write
to the shared reactive store and, when ``subscribe()`` is active,
re-execute automatically when their ^pointer dependencies change.
Formula execution follows topological order (dependencies first).

Lifecycle:
    1. ``__init__``: create builders via ``set_builder()``.
    2. ``setup()``: populate data and source (calls ``store()`` then ``main()``).
    3. ``build()``: materialize all builders (source -> built, two-pass:
       data elements first, then normal elements).
    4. ``subscribe()``: activate reactive bindings (optional). Enables
       formula re-execution on data changes, ``_delay`` debounce,
       ``_interval`` periodic execution, and ``suspend_output`` /
       ``resume_output`` for batched rendering.

Example — single builder:
    >>> class HtmlManager(BuilderManager):
    ...     def __init__(self):
    ...         self.page = self.set_builder('page', HtmlBuilder)
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
    ...         self.compose = self.set_builder('compose', ComposeBuilder)
    ...         self.traefik = self.set_builder('traefik', TraefikBuilder)
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
    >>> stack.setup()
    >>> stack.build()
    >>> stack.subscribe()
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

        ``store(data)``: Override to populate shared data at the store root.

        ``main(source)`` or ``main_<name>(source)``: Override to populate
            each builder's source Bag.

        ``setup()``: Orchestrates store → main. Call from ``__init__``.

        ``build()``: Materializes all builders (source → built).

        ``subscribe()``: Activates reactive bindings (optional).

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

    def build(self) -> None:
        """Materialize all builders: source → built."""
        for builder in self._builders.values():
            builder.build()

    def subscribe(self) -> None:
        """Activate reactive bindings on all builders."""
        for builder in self._builders.values():
            builder.subscribe()
