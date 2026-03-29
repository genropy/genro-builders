# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderManager — mixin to coordinate builders with shared data.

Provides a shared data Bag and builder registry. Subclass state
(_data, _builders) is initialized automatically via __init_subclass__,
so subclasses do not need to call super().__init__().

Example:
    >>> class MyPage(BuilderManager):
    ...     def __init__(self):
    ...         self.page = self.set_builder('page', HtmlBuilder)
    ...
    >>> page = MyPage()
    >>> page.data['title'] = 'Hello'
    >>> page.page.source.div(value='^title')
    >>> page.build_all()
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag


class BuilderManager:
    """Mixin to coordinate one or more builders with shared data.

    Subclasses get ``_data`` (Bag with backref) and ``_builders`` (dict)
    initialized automatically — no ``super().__init__()`` needed.
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
            name: Name for the builder (used by build_all).
            builder_class: The BagBuilderBase subclass to instantiate.
            **kwargs: Extra kwargs passed to the builder constructor.

        Returns:
            The created builder instance.
        """
        builder = builder_class(manager=self, **kwargs)
        self._builders[name] = builder
        return builder

    def build_all(self) -> None:
        """Build all registered builders."""
        for builder in self._builders.values():
            builder.build()
