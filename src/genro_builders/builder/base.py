# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagBuilderBase — grammar base class for Bag builders.

A builder declares the grammar of a dialect via decorators
(@element, @abstract, @subbuilder, @data_element) and the schema of
valid tag placements (sub_tags, parent_tags). Engine responsibilities
— source, the create/render phases, render_target, node_id index —
live on the BuilderHandler (decisions 1, 8, 9).

Exports:
    BagBuilderBase: Base class for all builders.
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Any

from genro_bag import Bag

from ..compiler import CompilerBase
from ..renderer import RendererBase
from ._grammar import _GrammarMixin
from ._utilities import _extract_validators_from_signature, _pop_decorated_methods


class BagBuilderBase(
    _GrammarMixin,
    ABC,
):
    """Abstract base class for Bag builders (grammar only).

    A builder declares the dialect via decorators:
        - @element: Pure schema elements (body MUST be empty)
        - @abstract: Define sub_tags for inheritance (cannot be instantiated)
        - @subbuilder: Switch the active grammar to a sub-dialect.
        - @data_element: Data-infrastructure elements.

    Engine concerns (source, lifecycle phases, render_target,
    node_id) belong to the BuilderHandler.
    """

    _class_schema: Bag  # Schema built from decorators at class definition
    _schema_path: str | Path | None = None  # Default schema path (class attribute)

    # -----------------------------------------------------------------------
    # Builder registry (class-level, shared across all dialects)
    # -----------------------------------------------------------------------

    #: Canonical name of this dialect (e.g. ``"html"``, ``"svg"``).
    #: Concrete dialects MUST declare ``_name`` as a class attribute to
    #: appear in :attr:`register`. Builders that leave ``_name = None``
    #: (the default) are not registered — useful for internal-only
    #: classes like ``SchemaBuilder``.
    _name: str | None = None

    #: Class-level dict mapping ``_name`` to the Builder class. Populated
    #: automatically in :meth:`__init_subclass__` whenever a subclass
    #: declares ``_name``. Lookup via :meth:`get_builder_class`.
    register: dict[str, type] = {}

    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Build _class_schema Bag from decorated methods (@element,
        @abstract, @subbuilder, @data_element)."""
        super().__init_subclass__(**kwargs)

        schema_path = getattr(cls, "_schema_path", None)
        if schema_path is not None:
            cls._class_schema = Bag().fill_from(schema_path)
        else:
            parent_schema = None
            for base in cls.__mro__[1:]:
                if hasattr(base, "_class_schema"):
                    parent_schema = base._class_schema
                    break
            cls._class_schema = Bag(source=parent_schema) if parent_schema else Bag()

        for tag_list, method_name, obj, decorator_info in _pop_decorated_methods(cls, BagBuilderBase):
            if method_name:
                setattr(cls, method_name, obj)

            is_data_element = decorator_info.get("data_element", False)
            is_subbuilder = decorator_info.get("subbuilder", False)
            sub_tags = decorator_info.get("sub_tags", "")
            parent_tags = decorator_info.get("parent_tags")
            inherits_from = decorator_info.get("inherits_from", "")
            meta = decorator_info.get("_meta")
            subbuilder_name = decorator_info.get("subbuilder_name")
            subbuilder_wrap_tag = decorator_info.get("wrap_tag")
            documentation = obj.__doc__
            call_args_validations = _extract_validators_from_signature(obj)

            for tag in tag_list:
                if is_data_element:
                    cls._class_schema.set_item(
                        tag, None,
                        handler_name=method_name,
                        is_data_element=True,
                        documentation=documentation,
                    )
                elif is_subbuilder:
                    cls._class_schema.set_item(
                        tag, None,
                        handler_name=method_name,
                        is_subbuilder=True,
                        subbuilder_name=subbuilder_name,
                        wrap_tag=subbuilder_wrap_tag,
                        parent_tags=parent_tags,
                        _meta=meta,
                        documentation=documentation,
                    )
                else:
                    cls._class_schema.set_item(
                        tag, None,
                        sub_tags=sub_tags,
                        parent_tags=parent_tags,
                        inherits_from=inherits_from,
                        _meta=meta,
                        documentation=documentation,
                        call_args_validations=call_args_validations,
                    )

        cls._schema_tag_names = frozenset(
            node.label for node in cls._class_schema.nodes
            if not node.label.startswith("@")
        )

        name = cls.__dict__.get("_name")
        if name is not None:
            if not isinstance(name, str):
                raise TypeError(
                    f"{cls.__name__}._name must be str, got {type(name).__name__}"
                )
            existing = BagBuilderBase.register.get(name)
            if existing is not None and existing is not cls:
                raise ValueError(
                    f"Builder name {name!r} already registered to "
                    f"{existing.__name__}; cannot register {cls.__name__}"
                )
            BagBuilderBase.register[name] = cls

    @classmethod
    def get_builder_class(cls, name: str) -> type:
        """Look up a registered Builder class by its canonical ``_name``.

        If ``name`` is not in the registry, attempts a lazy import of
        ``genro_builders.contrib.<name>`` to give the dialect a chance
        to register itself via ``__init_subclass__``. This keeps the
        ``@subbuilder("name")`` declarations decoupled from import
        order: mutual references (HTML <-> SVG) need not eagerly
        import each other.

        Raises:
            LookupError: if no builder is registered under ``name``
                after the auto-import attempt.
        """
        if name not in BagBuilderBase.register:
            try:
                __import__(f"genro_builders.contrib.{name}")
            except ImportError:
                pass
        try:
            return BagBuilderBase.register[name]
        except KeyError:
            raise LookupError(f"No builder registered with name {name!r}") from None

    def __init__(self) -> None:
        """Initialize the builder. Grammar-only state (decisions 1, 8)."""
        self._schema = type(self)._class_schema
        self._schema_tag_names = type(self)._schema_tag_names

    # -----------------------------------------------------------------------
    # Render & compile (decision 8, renegotiated 2026-05-12)
    # -----------------------------------------------------------------------

    #: Default rendering mode used when ``render(mode=None)`` is called.
    #: Concrete dialects override this (e.g. ``"html"`` for HtmlBuilder).
    _default_render_mode: str = "xml"

    #: Dialect renderer class. Subclasses bind their own renderer
    #: (e.g. ``HtmlRenderer`` for ``HtmlBuilder``). Defaults to the
    #: bare ``RendererBase`` which provides only ``render_xml`` —
    #: enough for plain XML dialects and for sanity tests.
    _renderer_class: type = RendererBase

    #: Dialect compiler class. Subclasses bind their own compiler
    #: (e.g. ``HtmlCompiler``). Defaults to the bare ``CompilerBase``
    #: stub whose ``compile`` raises ``NotImplementedError``.
    _compiler_class: type = CompilerBase
