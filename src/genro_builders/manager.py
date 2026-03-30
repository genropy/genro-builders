# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderManager — mixin to coordinate builders with shared data.

Provides a shared data Bag, builder registry, and declarative hooks
for populating data and structure. Subclass state is initialized
automatically via __init_subclass__ — no super().__init__() needed.

Hooks (override in subclass):
    reactive_store(data): Populate the shared data Bag with defaults.
    recipe(source): Populate the source of a single-builder manager.
    recipe_<name>(source): Populate the source of a named builder.

Example — single builder:
    >>> class MyPage(BuilderManager):
    ...     def __init__(self):
    ...         self.page = self.set_builder('page', HtmlBuilder)
    ...
    ...     def reactive_store(self, data):
    ...         data['title'] = 'Hello'
    ...
    ...     def recipe(self, source):
    ...         source.h1(value='^title')
    ...
    >>> page = MyPage()
    >>> page.build()
    >>> print(page.page.output)

Example — multiple builders:
    >>> class Report(BuilderManager):
    ...     def __init__(self):
    ...         self.excel = self.set_builder('excel', ExcelBuilder)
    ...         self.word = self.set_builder('word', WordBuilder)
    ...
    ...     def reactive_store(self, data):
    ...         data['company'] = 'Acme'
    ...
    ...     def recipe_excel(self, source):
    ...         source.workbook().sheet(name='^company')
    ...
    ...     def recipe_word(self, source):
    ...         source.document().heading(content='^company')
    ...
    >>> report = Report()
    >>> report.build()
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag


class BuilderManager:
    """Mixin to coordinate one or more builders with shared data.

    Subclasses get ``_data`` (Bag with backref) and ``_builders`` (dict)
    initialized automatically — no ``super().__init__()`` needed.

    Override ``reactive_store(data)`` to set initial data values.
    Override ``recipe(source)`` for single-builder managers, or
    ``recipe_<name>(source)`` for each named builder.

    Call ``build()`` to run the full pipeline:
    reactive_store → recipes → build_all.
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
        for builder in self._builders.values():
            builder._rebind_data(new_data)

    def set_builder(self, name: str, builder_class: type, **kwargs: Any) -> Any:
        """Create a builder, register it, and return it.

        Args:
            name: Name for the builder (used by build and recipe dispatch).
            builder_class: The BagBuilderBase subclass to instantiate.
            **kwargs: Extra kwargs passed to the builder constructor.

        Returns:
            The created builder instance.
        """
        builder = builder_class(manager=self, **kwargs)
        self._builders[name] = builder
        return builder

    def build(self) -> None:
        """Run the full pipeline: reactive_store → recipes → build_all.

        1. Calls ``reactive_store(self.data)`` if defined.
        2. For each builder named N, calls ``recipe_N(source)`` if defined.
           If only one builder and no ``recipe_N`` exists, calls ``recipe(source)``.
        3. Builds all registered builders.
        """
        if hasattr(self, "reactive_store"):
            self.reactive_store(self.data)

        for name, builder in self._builders.items():
            recipe_method = getattr(self, f"recipe_{name}", None)
            if recipe_method is not None:
                recipe_method(builder.source)
            elif len(self._builders) == 1:
                recipe = getattr(self, "recipe", None)
                if recipe is not None:
                    recipe(builder.source)

        self.build_all()

    def build_all(self) -> None:
        """Build all registered builders (without calling hooks)."""
        for builder in self._builders.values():
            builder.build()
