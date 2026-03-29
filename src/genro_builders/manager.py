# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderManager — coordinate multiple builders with shared data.

Registers named builders and provides a shared data Bag. When data
changes, all registered builders are rebound automatically.

Example:
    >>> class MyApp(BuilderManager):
    ...     def __init__(self):
    ...         super().__init__()
    ...         self.page = self.register_builder('page', HtmlBuilder)
    ...         self.sidebar = self.register_builder('sidebar', HtmlBuilder)
    ...
    >>> app = MyApp()
    >>> app.data['user.name'] = 'Alice'  # propagates to both builders
    >>> app.compile_all()
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag


class BuilderManager:
    """Mixin for managing multiple builders with shared data bus.

    Provides a registry of named builders and a shared data Bag.
    When data is replaced, all builders are rebound automatically.
    """

    def __init__(self) -> None:
        self._builder_registry: dict[str, Any] = {}
        self._data = Bag()
        self._data.set_backref()

    @property
    def data(self) -> Bag:
        """The shared data Bag."""
        return self._data

    @data.setter
    def data(self, value: Bag | dict[str, Any]) -> None:
        """Replace the shared data Bag. Rebinds all registered builders."""
        new_data = Bag(source=value) if isinstance(value, dict) else value
        if not new_data.backref:
            new_data.set_backref()
        self._data = new_data
        for builder in self._builder_registry.values():
            builder._rebind_data(new_data)

    def register_builder(self, name: str, builder_class: type, **kwargs: Any) -> Any:
        """Create and register a builder with this manager.

        Args:
            name: Unique name for the builder.
            builder_class: The BagBuilderBase subclass to instantiate.
            **kwargs: Extra kwargs passed to builder constructor.

        Returns:
            The created builder instance.
        """
        builder = builder_class(manager=self, **kwargs)
        self._builder_registry[name] = builder
        return builder

    def get_builder(self, name: str) -> Any:
        """Get a registered builder by name."""
        return self._builder_registry[name]

    def compile_all(self) -> None:
        """Compile all registered builders."""
        for builder in self._builder_registry.values():
            builder.compile()

    def on_builder_changed(self, builder: Any, event: str) -> None:
        """Hook called when a builder's state changes.

        Override in subclass for cross-builder orchestration.

        Args:
            builder: The builder that changed.
            event: Description of the change (e.g., 'compiled', 'data_changed').
        """
