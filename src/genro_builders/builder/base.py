# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagBuilderBase — base class for Bag builders with grammar and validation.

A builder is a machine: it defines a domain-specific grammar via decorators
(@element, @abstract, @component), materializes a source Bag into a built
Bag (expanding components and resolving ^pointers), and produces output via
named renderers (BagRendererBase, serialized) or compilers (BagCompilerBase,
live objects). A ``BuilderManager`` mixin coordinates one or more builders
with a shared reactive data store, providing the store/main hooks for
population and the setup/build/subscribe lifecycle.

Exports:
    BagBuilderBase: Base class for all builders.
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from genro_bag import Bag

from ..binding import BindingManager
from ..builder_bag import BuilderBag
from ._build_mixin import _BuildMixin
from ._decorators import data_element
from ._dispatch_mixin import _DispatchMixin
from ._output_mixin import _OutputMixin
from ._reactivity_mixin import _ReactivityMixin
from ._utilities import _extract_validators_from_signature, _pop_decorated_methods

if TYPE_CHECKING:
    from genro_bag import BagNode


class BagBuilderBase(
    _OutputMixin,
    _ReactivityMixin,
    _BuildMixin,
    _DispatchMixin,
    ABC,
):
    """Abstract base class for Bag builders.

    A builder provides domain-specific methods for creating nodes in a Bag.
    Define elements using decorators:
        - @element: Pure schema elements (body MUST be empty)
        - @abstract: Define sub_tags for inheritance (cannot be instantiated)
        - @component: Composite structures (body called at compile time only)

    Schema conventions:
        - Elements: stored directly by name (e.g., 'div', 'span')
        - Abstracts: prefixed with '@' (e.g., '@flow', '@phrasing')
        - Components: stored by name, marked with is_component=True

    Validation parameters:
        - sub_tags: Controls which children are allowed under this element
        - parent_tags: Controls where this element can be placed

    Schema loading priority:
        1. schema_path passed to constructor (builder_schema_path='...')
        2. schema_path class attribute
        3. @element and @component decorated methods

    Usage:
        >>> builder = MyBuilder()
        >>> builder.source.div()     # populate source
        >>> builder.build()          # materialize source -> built
        >>> builder.render()         # produce output
    """

    _class_schema: Bag  # Schema built from decorators at class definition
    _schema_path: str | Path | None = None  # Default schema path (class attribute)
    _compiler_class: type | None = None  # Legacy: default compiler class
    _renderers: ClassVar[dict[str, type]] = {}  # Named renderer classes
    _compilers: ClassVar[dict[str, type]] = {}  # Named compiler classes

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
            # Inherit parent schema via MRO, then extend with own elements
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
            # For components: distinguish between sub_tags="" (closed) and absent (open)
            # Use sentinel to detect if sub_tags was explicitly set
            sub_tags = decorator_info.get("sub_tags") if is_component else decorator_info.get("sub_tags", "")
            parent_tags = decorator_info.get("parent_tags")
            inherits_from = decorator_info.get("inherits_from", "")
            meta = decorator_info.get("_meta")
            component_builder = decorator_info.get("builder")
            based_on = decorator_info.get("based_on")
            component_slots = decorator_info.get("slots")
            documentation = obj.__doc__
            call_args_validations = _extract_validators_from_signature(obj)

            for tag in tag_list:
                if is_data_element:
                    cls._class_schema.set_item(
                        tag,
                        None,
                        handler_name=method_name,
                        is_data_element=True,
                        documentation=documentation,
                    )
                elif is_component:
                    cls._class_schema.set_item(
                        tag,
                        None,
                        handler_name=method_name,
                        is_component=True,
                        component_builder=component_builder,
                        based_on=based_on,
                        slots=component_slots,
                        sub_tags=sub_tags,
                        parent_tags=parent_tags,
                        _meta=meta,
                        documentation=documentation,
                        call_args_validations=call_args_validations,
                    )
                else:
                    # Element: no adapter_name (body must be empty)
                    cls._class_schema.set_item(
                        tag,
                        None,
                        sub_tags=sub_tags,
                        parent_tags=parent_tags,
                        inherits_from=inherits_from,
                        _meta=meta,
                        documentation=documentation,
                        call_args_validations=call_args_validations,
                    )

        # Precompute schema tag names for fast lookup in BuilderBag.__getattribute__
        cls._schema_tag_names = frozenset(
            node.label for node in cls._class_schema.nodes
            if not node.label.startswith("@")
        )

    def __init__(
        self,
        bag: Bag | None = None,
        schema_path: str | Path | None = None,
        *,
        manager: Any = None,
        data: Bag | None = None,
    ) -> None:
        """Initialize the builder.

        Creates source, built, data, binding, and compiler internally.
        If a ``manager`` is provided, data is shared across all builders
        registered with that manager.

        Args:
            bag: Reserved for internal use by BuilderBag. Do not pass
                directly -- instantiate the builder with no arguments.
            schema_path: Optional path to load a pre-compiled schema from.
            manager: Optional BuilderManager for shared data coordination.
            data: Optional initial data Bag.
        """
        if schema_path is not None:
            self._schema = Bag().fill_from(schema_path)
        else:
            self._schema = type(self)._class_schema
        self._schema_tag_names = frozenset(
            node.label for node in self._schema.nodes
            if not node.label.startswith("@")
        )

        self._node_id_map: dict[str, BagNode] = {}

        if bag is not None:
            # Internal: BuilderBag passes itself as bag
            self._bag = bag
            self._bag.set_backref()
            self._manager = None
            self._data = data if data is not None else Bag()
        else:
            # Standard instantiation: builder owns the full pipeline
            self._manager = manager

            self._source_shell = BuilderBag(builder=type(self))
            self._source_shell.set_backref()
            self._source_shell.set_item("root", BuilderBag(builder=type(self)))

            self._built_shell = BuilderBag(builder=type(self))
            self._built_shell.set_backref()
            self._built_shell.set_item("root", BuilderBag(builder=type(self)))

            self._bag = self._source_shell.get_item("root")

            self._data = data if data is not None else Bag()
            if not self._data.backref:
                self._data.set_backref()

            self._binding = BindingManager(on_node_updated=self._on_node_updated)
            self._formula_registry: dict[str, dict[str, Any]] = {}
            self._active_timers: dict[str, str] = {}  # entry_id -> timer_id
            self._auto_compile = False
            self._output_suspended = False
            self._output_pending = False
            self._output: str | None = None

            # Instantiate registered renderers and compilers
            self._renderer_instances: dict[str, Any] = {
                name: cls(self) for name, cls in type(self)._renderers.items()
            }
            self._compiler_instances: dict[str, Any] = {
                name: cls(self) for name, cls in type(self)._compilers.items()
            }

            # Legacy: _compiler_class -> single compiler instance
            compiler_cls = getattr(type(self), "_compiler_class", None)
            if compiler_cls:
                self._compiler_instance = compiler_cls(self)
            else:
                self._compiler_instance = None

    # -----------------------------------------------------------------------
    # Built-in data elements
    # -----------------------------------------------------------------------

    @data_element()
    def data_setter(self, path, value=None, **kwargs):
        """Static data: write value at path in data Bag."""
        return path, dict(value=value, **kwargs)

    @data_element()
    def data_formula(self, path, func=None, **kwargs):
        """Computed data: call func with resolved kwargs, write result at path."""
        return path, dict(func=func, **kwargs)

    @data_element()
    def data_controller(self, func=None, **kwargs):
        """Controller: call func with resolved kwargs."""
        return None, dict(func=func, **kwargs)

    # -----------------------------------------------------------------------
    # Pipeline properties
    # -----------------------------------------------------------------------

    @property
    def source(self) -> BuilderBag:
        """The source Bag where elements are added."""
        return self._source_shell.get_item("root")

    @property
    def built(self) -> BuilderBag:
        """The built Bag (components expanded, pointers resolved)."""
        return self._built_shell.get_item("root")

    @property
    def data(self) -> Bag:
        """The data Bag. Shared with the manager when one is present."""
        if self._manager is not None:
            return self._manager.reactive_store
        return self._data

    @data.setter
    def data(self, value: Bag | dict[str, Any]) -> None:
        """Replace the data Bag. Delegates to the manager when present."""
        if self._manager is not None:
            self._manager.reactive_store = value
            return
        new_data = Bag(source=value) if isinstance(value, dict) else value
        if not new_data.backref:
            new_data.set_backref()
        self._data = new_data
        if self._auto_compile:
            self._binding.rebind(new_data)
            self._rerender()

    @property
    def output(self) -> str | None:
        """Last rendered output string, or None before first compile."""
        return self._output
