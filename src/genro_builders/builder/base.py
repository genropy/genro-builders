# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagBuilderBase — grammar base class for Bag builders.

A builder declares the grammar of a dialect via decorators
(@element, @abstract, @component) and the schema of valid tag
placements (sub_tags, parent_tags). Engine responsibilities — source,
built, the create/build/render phases, render_target, node_id index —
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
from ._build import _BuildMixin
from ._component import _ComponentMixin
from ._grammar import _GrammarMixin
from ._utilities import _extract_validators_from_signature, _pop_decorated_methods


class BagBuilderBase(
    _BuildMixin,
    _ComponentMixin,
    _GrammarMixin,
    ABC,
):
    """Abstract base class for Bag builders (grammar only).

    A builder declares the dialect via decorators:
        - @element: Pure schema elements (body MUST be empty)
        - @abstract: Define sub_tags for inheritance (cannot be instantiated)
        - @component: Composite structures (body called at expand time only)

    Engine concerns (source/built bags, the three lifecycle phases,
    render_target, node_id) belong to the BuilderHandler.
    """

    _class_schema: Bag  # Schema built from decorators at class definition
    _schema_path: str | Path | None = None  # Default schema path (class attribute)

    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Build _class_schema Bag from @element and @component decorated methods."""
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

            is_component = decorator_info.get("component", False)
            is_data_element = decorator_info.get("data_element", False)
            is_subbuilder = decorator_info.get("subbuilder", False)
            sub_tags = decorator_info.get("sub_tags") if is_component else decorator_info.get("sub_tags", "")
            parent_tags = decorator_info.get("parent_tags")
            inherits_from = decorator_info.get("inherits_from", "")
            meta = decorator_info.get("_meta")
            component_builder = decorator_info.get("builder")
            based_on = decorator_info.get("based_on")
            component_slots = decorator_info.get("slots")
            main_tag = decorator_info.get("main_tag")
            subbuilder_class = decorator_info.get("subbuilder_class")
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
                elif is_component:
                    cls._class_schema.set_item(
                        tag, None,
                        handler_name=method_name,
                        is_component=True,
                        main_tag=main_tag,
                        component_builder=component_builder,
                        based_on=based_on,
                        slots=component_slots,
                        sub_tags=sub_tags,
                        parent_tags=parent_tags,
                        _meta=meta,
                        documentation=documentation,
                        call_args_validations=call_args_validations,
                    )
                elif is_subbuilder:
                    cls._class_schema.set_item(
                        tag, None,
                        is_subbuilder=True,
                        subbuilder_class=subbuilder_class,
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
