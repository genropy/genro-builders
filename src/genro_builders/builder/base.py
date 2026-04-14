# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagBuilderBase — base class for Bag builders with grammar and validation.

A builder is a machine: it defines a domain-specific grammar via decorators
(@element, @abstract, @component), materializes a source Bag into a built
Bag (expanding components and resolving ^pointers), and produces output via
named renderers (BagRendererBase, serialized) or compilers (BagCompilerBase,
live objects).

Reactivity (subscribe, formula re-execution, timers, incremental compile)
is encapsulated in ``ReactivityEngine``, created lazily on first
``subscribe()`` call.

Exports:
    BagBuilderBase: Base class for all builders.
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from genro_bag import Bag

from ..builder_bag import BuilderBag
from ..built_bag import BuiltBag
from ._build import _BuildMixin
from ._component import _ComponentMixin
from ._decorators import data_element
from ._grammar import _GrammarMixin
from ._output import _OutputMixin
from ._utilities import _extract_validators_from_signature, _pop_decorated_methods

if TYPE_CHECKING:
    from genro_bag import BagNode

    from ._reactivity import ReactivityEngine


class BagBuilderBase(
    _OutputMixin,
    _BuildMixin,
    _ComponentMixin,
    _GrammarMixin,
    ABC,
):
    """Abstract base class for Bag builders.

    A builder provides domain-specific methods for creating nodes in a Bag.
    Define elements using decorators:
        - @element: Pure schema elements (body MUST be empty)
        - @abstract: Define sub_tags for inheritance (cannot be instantiated)
        - @component: Composite structures (body called at compile time only)

    Reactivity is optional: call ``subscribe()`` to activate formula
    re-execution, timers, incremental compile, and output management.
    Without subscribe, the builder is a pure grammar + build + render machine.

    Usage:
        >>> builder = MyBuilder()
        >>> builder.source.div()     # populate source
        >>> builder.build()          # materialize source -> built
        >>> builder.render()         # produce output
    """

    _class_schema: Bag  # Schema built from decorators at class definition
    _schema_path: str | Path | None = None  # Default schema path (class attribute)
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
            sub_tags = decorator_info.get("sub_tags") if is_component else decorator_info.get("sub_tags", "")
            parent_tags = decorator_info.get("parent_tags")
            inherits_from = decorator_info.get("inherits_from", "")
            meta = decorator_info.get("_meta")
            component_builder = decorator_info.get("builder")
            based_on = decorator_info.get("based_on")
            component_slots = decorator_info.get("slots")
            main_tag = decorator_info.get("main_tag")
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

    def __init__(
        self,
        bag: Bag | None = None,
        schema_path: str | Path | None = None,
        *,
        manager: Any = None,
        data: Bag | None = None,
    ) -> None:
        """Initialize the builder.

        Args:
            bag: Reserved for internal use by BuilderBag.
            schema_path: Optional path to load a pre-compiled schema from.
            manager: Optional BuilderManager for shared data coordination.
            data: Optional initial data Bag.
        """
        # Grammar
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
            self._reactivity: ReactivityEngine | None = None
        else:
            # Standard instantiation: builder owns the full pipeline
            self._manager = manager

            # Shells wrap the root Bags so that set_backref() gives root
            # nodes a parent reference, needed for fullpath resolution.
            self._source_shell = BuilderBag(builder=type(self))
            self._source_shell.set_backref()
            self._source_shell.set_item("root", BuilderBag(builder=type(self)))

            self._built_shell = BuiltBag()
            self._built_shell.set_backref()
            self._built_shell.set_item("root", BuiltBag())

            self._bag = self._source_shell.get_item("root")

            self._source_shell._pipeline_builder = self

            # Data
            self._data = data if data is not None else Bag()
            if not self._data.backref:
                self._data.set_backref()

            # Output
            self._renderer_instances: dict[str, Any] = {
                name: cls(self) for name, cls in type(self)._renderers.items()
            }
            self._compiler_instances: dict[str, Any] = {
                name: cls(self) for name, cls in type(self)._compilers.items()
            }

            # Reactivity: None until subscribe() is called
            self._reactivity: ReactivityEngine | None = None

    # -----------------------------------------------------------------------
    # Built-in data elements
    # -----------------------------------------------------------------------

    @data_element()
    def data_setter(self, path, value=None, **kwargs):
        """Static data: write value at path in data Bag."""
        return path, dict(value=value, **kwargs)

    @data_element()
    def data_formula(self, path: str, func: Callable, **kwargs: Any):
        """Computed data: call func with resolved kwargs, write result at path."""
        return path, dict(func=func, **kwargs)

    @data_element()
    def data_controller(self, func: Callable, **kwargs: Any):
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
    def built(self) -> BuiltBag:
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
        """Replace the data Bag. Delegates to manager or reactivity engine."""
        if self._manager is not None:
            self._manager.reactive_store = value
            return
        new_data = Bag(source=value) if isinstance(value, dict) else value
        if not new_data.backref:
            new_data.set_backref()
        self._data = new_data
        if self._reactivity is not None:
            self._reactivity.rebind_data(new_data)

    @property
    def output(self) -> str | None:
        """Last rendered output string, or None before first subscribe."""
        if self._reactivity is not None:
            return self._reactivity.output
        return None

    # -----------------------------------------------------------------------
    # Reactivity (delegated to ReactivityEngine)
    # -----------------------------------------------------------------------

    def subscribe(self) -> None:
        """Activate reactive bindings on the built Bag.

        Enables formula re-execution, timers, incremental compile,
        and output management. The ReactivityEngine is created
        lazily by build() if not already present.
        """
        self._ensure_reactivity()
        self._reactivity.subscribe()

    def rebuild(self, main: Any = None) -> None:
        """Full rebuild: clear source, optionally re-populate, build."""
        if self._reactivity is not None:
            self._reactivity.rebuild(main)
        else:
            self._clear_source()
            if main is not None:
                main(self.source)
            self.build()

    def suspend_output(self) -> None:
        """Suspend render/compile output."""
        if self._reactivity is not None:
            self._reactivity.suspend_output()

    def resume_output(self) -> None:
        """Resume render/compile output."""
        if self._reactivity is not None:
            self._reactivity.resume_output()

    @property
    def _binding(self) -> Any:
        """Access the binding manager (lives in ReactivityEngine)."""
        if self._reactivity is not None:
            return self._reactivity.binding
        return None

    @property
    def _auto_compile(self) -> bool:
        """Whether incremental compile is active (lives in ReactivityEngine)."""
        if self._reactivity is not None:
            return self._reactivity._auto_compile
        return False

    def _rebind_data(self, new_data: Bag) -> None:
        """Rebind to new data. Called by BuilderManager."""
        if self._reactivity is not None:
            self._reactivity.rebind_data(new_data)
