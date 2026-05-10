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
    # Render (decision 6)
    # -----------------------------------------------------------------------

    #: Default rendering mode used when ``render(mode=None)`` is called.
    #: Concrete dialects override this (e.g. ``"html"`` for HtmlBuilder).
    _default_render_mode: str = "xml"

    def render(
        self,
        built: Bag,
        mode: str | None = None,
        render_target: Any = None,
    ) -> Any:
        """Dispatch to the requested render mode.

        ``mode is None`` -> the dialect's default mode (class attribute
        ``_default_render_mode``).

        ``render_target is None`` -> the rendered output is returned
        as a string. Otherwise the concrete ``render_<mode>`` method
        writes into the target and may return ``None``.
        """
        effective_mode = mode if mode is not None else self._default_render_mode
        method_name = f"render_{effective_mode}"
        # Walk the class MRO directly: ``getattr(self, ...)`` would hit
        # ``_GrammarMixin.__getattr__`` and pretend any name resolves
        # to a schema-tag wrapper.
        method = None
        for klass in type(self).__mro__:
            if method_name in klass.__dict__:
                method = klass.__dict__[method_name]
                break
        if method is None:
            raise ValueError(
                f"{type(self).__name__} does not support render mode "
                f"'{effective_mode}' (no method '{method_name}')",
            )
        return method(self, built, render_target=render_target)

    def render_xml(self, built: Bag, render_target: Any = None) -> str | None:
        """Default XML render: serialize the built bag with ``to_xml()``.

        Concrete dialects can override to produce a richer XML (e.g.
        HTML-conforming auto-closing of void tags). When
        ``render_target`` is None the serialized string is returned;
        otherwise it is written to the target's ``write`` method (if
        any) or fed to the target as a callable.
        """
        text = built.to_xml()
        if render_target is None:
            return text
        write = getattr(render_target, "write", None)
        if callable(write):
            write(text)
            return None
        if callable(render_target):
            render_target(text)
            return None
        raise TypeError(
            f"render_target {render_target!r} is neither writable "
            "(.write) nor callable",
        )
