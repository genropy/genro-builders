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
    element: Decorator to mark methods as element handlers.
    abstract: Decorator to define abstract elements (for inheritance only).
    component: Decorator to mark methods as component handlers (lazy expansion).
    BagBuilderBase: Base class for all builders.
    SchemaBuilder: Builder for creating schemas programmatically.
    Regex: Regex pattern constraint for string validation.
    Range: Range constraint for numeric validation.

Decorators:
    @element: Pure schema elements. Body MUST be empty (...). No logic allowed.
    @abstract: Define sub_tags for inheritance. Cannot be instantiated directly.
    @component: Composite structures with required handler body. Body is called
        only at compile time (lazy expansion). Components can use a different
        builder internally.

Schema conventions:
    - Elements stored by name: 'div', 'span'
    - Abstracts prefixed with '@': '@flow', '@phrasing'
    - Use inherits_from='@abstract' to inherit sub_tags (only for @element)

Validation parameters:
    sub_tags: Controls which children are allowed (with cardinality).
    parent_tags: Controls where the element can be placed (comma-separated list).

sub_tags semantics:
    None     -> no validation (sub_tags not specified)
    ""       -> leaf element (no children allowed)
    "*"      -> accepts any children (container)
    "foo"    -> accepts only "foo" children

sub_tags cardinality syntax (when not "*"):
    foo      -> any number (0..N)
    foo[1]   -> exactly 1
    foo[3]   -> exactly 3
    foo[0:]  -> 0 or more
    foo[:2]  -> 0 to 2
    foo[1:3] -> 1 to 3

_meta parameter:
    All decorators (@element, @abstract, @component) accept a ``_meta`` dict
    for storing arbitrary metadata used by renderers and compilers:
        _meta={'compile_class': 'Container', 'renderer_svg_style': 'rounded'}

    When using inherits_from, _meta is inherited from the abstract
    and merged with the element's own _meta (element overrides abstract).

Constraint classes for use with Annotated:
    Regex: regex pattern for strings
    Range: min/max value constraints for numbers (ge, le, gt, lt)

Type hints supported:
    - Basic types: int, str, bool, float, Decimal
    - Literal['a', 'b'] for enum-like constraints
    - list[T], dict[K, V], tuple[...], set[T] for generics
    - X | None for optional
    - Annotated[T, validator...] for validators

Example - @element:
    >>> from genro_builders import BuilderBag
    >>> from genro_builders.builders import BagBuilderBase, element

    >>> class MyBuilder(BagBuilderBase):
    ...     @element(sub_tags='item')
    ...     def container(self): ...
    ...
    ...     @element(parent_tags='container')  # can only be inside container
    ...     def item(self): ...

Example - @component (lazy expansion):
    >>> from genro_builders import BuilderBag
    >>> from genro_builders.builders import BagBuilderBase, element, component

    >>> class FormBuilder(BagBuilderBase):
    ...     @element()
    ...     def input(self): ...
    ...
    ...     @component(sub_tags='')  # closed component, returns parent
    ...     def login_form(self, component: Bag, **kwargs):
    ...         # Body called only at compile time, not at creation
    ...         component.input(name='username')
    ...         component.input(name='password')

Example - Builder as a machine (direct usage in tests):
    >>> builder = MyBuilder()
    >>> builder.source.div(id='main').p('Hello')
    >>> builder.build()           # materialize source → built
    >>> print(builder.render())   # produce output

Example - BuilderManager with store/main hooks:
    >>> from genro_builders import BuilderManager
    >>>
    >>> class HtmlManager(BuilderManager):
    ...     def __init__(self):
    ...         self.page = self.set_builder('page', HtmlBuilder)
    ...     def render(self):
    ...         return self.page.render()
    >>>
    >>> class SalesPage(HtmlManager):
    ...     def __init__(self):
    ...         super().__init__()
    ...         self.setup()      # store → main
    ...         self.build()      # source → built
    ...     def store(self, data):
    ...         data['title'] = 'Hello'
    ...     def main(self, source):
    ...         source.h1(value='^title')
    >>>
    >>> page = SalesPage()
    >>> print(page.render())

Example - node_id for direct node lookup:
    >>> builder = MyBuilder()
    >>> builder.source.div(node_id='header').p('Title')
    >>> node = builder.node_by_id('header')  # O(1) lookup

SchemaBuilder Example:
    >>> from genro_builders import BuilderBag
    >>> from genro_builders.builders import SchemaBuilder
    >>>
    >>> schema = BuilderBag(builder=SchemaBuilder)
    >>> schema.item('@container', sub_tags='child', _meta={'compile_module': 'textual.containers'})
    >>> schema.item('vertical', inherits_from='@container', _meta={'compile_class': 'Vertical'})
    >>> schema.item('br', sub_tags='')  # void element
    >>> schema.builder._compile('schema.msgpack')
"""

from __future__ import annotations

import inspect
import re
import sys
import types
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Literal,
    get_args,
    get_origin,
    get_type_hints,
)

from genro_bag import Bag
from genro_toolbox.smarttimer import cancel_timer, set_interval, set_timeout

from .binding import BindingManager
from .builder_bag import BuilderBag
from .pointer import is_pointer, parse_pointer, scan_for_pointers

if TYPE_CHECKING:
    from genro_bag import BagNode


# =============================================================================
# Empty body detection (internal, needed by decorators)
# =============================================================================


def _ref_empty_body(self): ...


def _ref_empty_body_with_docstring(self):
    """docstring"""
    ...


_EMPTY_BODY_BYTECODE = _ref_empty_body.__code__.co_code
_EMPTY_BODY_DOCSTRING_BYTECODE = _ref_empty_body_with_docstring.__code__.co_code


def _is_empty_body(func: Callable) -> bool:
    """Check if function body is empty (just ... or docstring + ...)."""
    code = func.__code__.co_code
    return code in (_EMPTY_BODY_BYTECODE, _EMPTY_BODY_DOCSTRING_BYTECODE)


# =============================================================================
# Decorators (Public API)
# =============================================================================


def element(
    tags: str | tuple[str, ...] | None = None,
    sub_tags: str | tuple[str, ...] | None = None,
    parent_tags: str | None = None,
    inherits_from: str | None = None,
    _meta: dict[str, Any] | None = None,
) -> Callable:
    """Decorator to mark a method as element handler.

    Args:
        tags: Tag names this method handles. If None, uses method name.
        sub_tags: Valid child tags with cardinality. Syntax:
            'a,b,c'     -> a, b, c each exactly once
            'a[],b[]'   -> a and b any number of times
            'a[2],b[0:]' -> a exactly twice, b zero or more
            '' (empty)  -> no children allowed (void element)
        parent_tags: Valid parent tags (comma-separated). If specified,
            element can only be placed inside one of these parents.
        inherits_from: Abstract element name to inherit sub_tags from.
        _meta: Dict of metadata for renderers/compilers (e.g.
            compile_class, compile_module, renderer_svg_style).

    Example:
        @element(sub_tags='header,content[],footer')
        def page(self): ...

        @element(
            sub_tags='child',
            _meta={'compile_module': 'textual.containers', 'compile_class': 'Container'},
        )
        def container(self): ...

        @element(parent_tags='ul,ol')  # can only be inside ul or ol
        def li(self): ...
    """
    def decorator(func: Callable) -> Callable:
        # Elements MUST have empty body (ellipsis only)
        if not _is_empty_body(func):
            raise ValueError(
                f"@element '{func.__name__}' must have empty body (...) - "
                "use @component for elements with logic"
            )

        func._decorator = {  # type: ignore[attr-defined]
            k: v
            for k, v in {
                "tags": tags,
                "sub_tags": sub_tags,
                "parent_tags": parent_tags,
                "inherits_from": inherits_from,
                "_meta": _meta,
            }.items()
            if v is not None
        }
        return func

    return decorator


def abstract(
    sub_tags: str | tuple[str, ...] = "",
    parent_tags: str | tuple[str, ...] | None = None,
    inherits_from: str | None = None,
    _meta: dict[str, Any] | None = None,
) -> Callable:
    """Decorator to define an abstract element (for inheritance only).

    Abstract elements are stored with '@' prefix and cannot be instantiated.
    They define sub_tags/parent_tags that can be inherited by concrete elements.

    Args:
        sub_tags: Valid child tags with cardinality (see element decorator).
        parent_tags: Valid parent tags with cardinality.
        inherits_from: Comma-separated list of abstract names to inherit from.
        _meta: Dict of metadata for renderers/compilers.

    Example:
        @abstract(sub_tags='span,a,em,strong')
        def phrasing(self): ...

        @element(inherits_from='@phrasing')
        def p(self): ...

        @abstract(
            sub_tags='child',
            _meta={'compile_module': 'textual.containers'},
        )
        def base_container(self): ...
    """
    def decorator(func: Callable) -> Callable:
        result: dict[str, Any] = {
            "abstract": True,
            "sub_tags": sub_tags,
            "inherits_from": inherits_from or "",
        }
        if parent_tags is not None:
            result["parent_tags"] = parent_tags
        if _meta:
            result["_meta"] = _meta
        func._decorator = result  # type: ignore[attr-defined]
        return func

    return decorator


def component(
    tags: str | tuple[str, ...] | None = None,
    sub_tags: str | tuple[str, ...] | None = None,
    parent_tags: str | None = None,
    builder: type[BagBuilderBase] | None = None,
    based_on: str | None = None,
    _meta: dict[str, Any] | None = None,
    slots: list[str] | None = None,
) -> Callable:
    """Decorator to mark a method as component handler.

    Components are composite structures that receive a new Bag, populate it,
    and return it. The populated bag becomes the node's value.

    Unlike @element, @component REQUIRES a method body (ellipsis not allowed).
    The handler receives a fresh Bag as first parameter (after self) and
    should populate it with child elements.

    Args:
        tags: Tag names this component handles. If None, uses method name.
        sub_tags: Valid child tags AFTER the component is created. Controls
            return behavior of the component call:
            - '' (empty string): Closed/leaf component, returns parent bag
              (for chaining at same level)
            - defined or None: Open container, returns internal bag
              (for adding children to the component)
        parent_tags: Valid parent tags (comma-separated). If specified,
            component can only be placed inside one of these parents.
        builder: Optional builder class for the component's internal bag.
            If not specified, uses the same builder class as parent.
        _meta: Dict of metadata for renderers/compilers.
        slots: List of named slot names. When present, the component call
            returns a ComponentProxy with slot Bags accessible as attributes.
            The handler body should return a dict mapping slot names to
            destination Bags where slot content will be mounted.

    Handler signature (without slots):
        def handler(self, component: Bag, **kwargs) -> None:
            # 'component' is the component's internal Bag to populate
            # Body is called ONLY at compile time (lazy expansion)

    Handler signature (with slots):
        def handler(self, component: Bag, **kwargs) -> dict[str, Bag]:
            # Return dict mapping slot name → destination Bag
            # Slot content is mounted into destination Bags at compile time

    Example - Closed component (sub_tags=''):
        @component(sub_tags='')
        def login_form(self, component: Bag, **kwargs):
            component.input(name='username')
            component.input(name='password')
            component.button('Login')

        page.login_form()
        page.other_element()  # continues at same level

    Example - Open component (sub_tags defined):
        @component(sub_tags='item')
        def mylist(self, component: Bag, title='', **kwargs):
            component.header(title=title)

        lst = page.mylist(title='My List')
        lst.item('First')
        lst.item('Second')
    """
    def decorator(func: Callable) -> Callable:
        # Components MUST have a real body (not ellipsis)
        if _is_empty_body(func):
            raise ValueError(
                f"@component '{func.__name__}' must have a body - ellipsis (...) not allowed"
            )

        func._decorator = {  # type: ignore[attr-defined]
            k: v
            for k, v in {
                "component": True,
                "tags": tags,
                "sub_tags": sub_tags,
                "parent_tags": parent_tags,
                "builder": builder,
                "based_on": based_on,
                "_meta": _meta,
                "slots": slots,
            }.items()
            if v is not None
        }
        return func

    return decorator


def data_element(
    tags: str | tuple[str, ...] | None = None,
) -> Callable:
    """Decorator for data infrastructure elements.

    Data elements have a preprocessor body that returns (path, attrs_dict).
    They are transparent in sub_tags validation and NOT materialized in built.

    The handler body receives the raw arguments and returns a tuple:
        (path, attrs_dict) where path is the data path (None for controllers)
        and attrs_dict is a dict of attributes.

    Args:
        tags: Tag names this method handles. If None, uses method name.
    """
    def decorator(func: Callable) -> Callable:
        if _is_empty_body(func):
            raise ValueError(
                f"@data_element '{func.__name__}' must have a body"
            )
        func._decorator = {  # type: ignore[attr-defined]
            "data_element": True,
            "tags": tags,
        }
        return func

    return decorator


# =============================================================================
# Validator classes (Annotated metadata)
# =============================================================================


@dataclass(frozen=True)
class Regex:
    """Regex pattern constraint for string validation."""

    pattern: str
    flags: int = 0

    def __call__(self, value: Any) -> None:
        if not isinstance(value, str):
            raise TypeError("Regex validator requires a str")
        if re.fullmatch(self.pattern, value, self.flags) is None:
            raise ValueError(f"must match pattern '{self.pattern}'")


@dataclass(frozen=True)
class Range:
    """Range constraint for numeric validation (Pydantic-style: ge, le, gt, lt)."""

    ge: float | None = None
    le: float | None = None
    gt: float | None = None
    lt: float | None = None

    def __call__(self, value: Any) -> None:
        if not isinstance(value, (int, float, Decimal)):
            raise TypeError("Range validator requires int, float or Decimal")
        if self.ge is not None and value < self.ge:
            raise ValueError(f"must be >= {self.ge}")
        if self.le is not None and value > self.le:
            raise ValueError(f"must be <= {self.le}")
        if self.gt is not None and value <= self.gt:
            raise ValueError(f"must be > {self.gt}")
        if self.lt is not None and value >= self.lt:
            raise ValueError(f"must be < {self.lt}")


# =============================================================================
# BagBuilderBase
# =============================================================================


class BagBuilderBase(ABC):
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
        >>> builder.build()          # materialize source → built
        >>> builder.render()         # produce output
    """

    _class_schema: Bag  # Schema built from decorators at class definition
    _schema_path: str | Path | None = None  # Default schema path (class attribute)
    _compiler_class: type | None = None  # Legacy: default compiler class
    _renderers: ClassVar[dict[str, type]] = {}  # Named renderer classes
    _compilers: ClassVar[dict[str, type]] = {}  # Named compiler classes

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

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

        for tag_list, method_name, obj, decorator_info in _pop_decorated_methods(cls):
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
                directly — instantiate the builder with no arguments.
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
            self._active_timers: dict[str, str] = {}  # entry_id → timer_id
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

            # Legacy: _compiler_class → single compiler instance
            compiler_cls = getattr(type(self), "_compiler_class", None)
            if compiler_cls:
                self._compiler_instance = compiler_cls(self)
            else:
                self._compiler_instance = None

    # -------------------------------------------------------------------------
    # Built-in data elements
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Pipeline properties
    # -------------------------------------------------------------------------

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

    def _rebind_data(self, new_data: Bag) -> None:
        """Rebind this builder to new data. Called by BuilderManager."""
        if self._auto_compile:
            self._binding.rebind(new_data)
            self._rerender()

    def _on_node_updated(self, node: BagNode) -> None:
        """Called by BindingManager when a bound node is updated."""
        if self._auto_compile:
            self._rerender()

    def _rerender(self) -> None:
        """Re-render the built bag without re-building.

        If output is suspended, marks as pending and returns.
        The actual render happens on resume_output().
        """
        if self._output_suspended:
            self._output_pending = True
            return
        self._output = self.render(self.built)

    def suspend_output(self) -> None:
        """Suspend render/compile output.

        While suspended, data changes and formula re-executions still
        happen normally, but no render/compile is triggered.
        Call resume_output() to flush a single render.
        """
        self._output_suspended = True

    def resume_output(self) -> None:
        """Resume render/compile output.

        If any render was pending during suspension, triggers one now.
        """
        self._output_suspended = False
        if self._output_pending:
            self._output_pending = False
            self._rerender()

    # -------------------------------------------------------------------------
    # Formula/controller reactivity
    # -------------------------------------------------------------------------

    def _topological_sort_formulas(self) -> list[str]:
        """Sort formula entries by dependency order. Detect cycles.

        Builds a DAG from formula dependencies: if formula A writes to
        path X, and formula B has ^X in its kwargs, then A must execute
        before B.

        Returns:
            List of entry_ids in execution order (dependencies first).

        Raises:
            ValueError: If a circular dependency is detected.
        """
        if not self._formula_registry:
            return []

        # Build: path → entry_id (which formula writes to which path)
        path_to_entry: dict[str, str] = {}
        for entry_id, entry in self._formula_registry.items():
            if entry["path"] is not None:
                path_to_entry[entry["path"]] = entry_id

        # Build adjacency: entry_id → set of entry_ids it depends on
        deps: dict[str, set[str]] = {eid: set() for eid in self._formula_registry}
        for entry_id, entry in self._formula_registry.items():
            for v in entry["raw_attrs"].values():
                if is_pointer(v):
                    dep_path = self._resolve_pointer_path(v, entry["node"])
                    dep_entry = path_to_entry.get(dep_path)
                    if dep_entry is not None and dep_entry != entry_id:
                        deps[entry_id].add(dep_entry)

        # Topological sort (Kahn's algorithm)
        visited: set[str] = set()
        in_stack: set[str] = set()
        order: list[str] = []

        def visit(eid: str) -> None:
            if eid in in_stack:
                cycle_path = self._formula_registry[eid].get("path", eid)
                raise ValueError(
                    f"Circular dependency in data_formula: {cycle_path}"
                )
            if eid in visited:
                return
            in_stack.add(eid)
            for dep_eid in deps.get(eid, ()):
                visit(dep_eid)
            in_stack.discard(eid)
            visited.add(eid)
            order.append(eid)

        for eid in self._formula_registry:
            visit(eid)

        return order

    def _on_formula_data_changed(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Re-execute formula/controller when their dependencies change.

        Uses _formula_order (topological sort) to ensure dependent formulas
        execute after their dependencies. Cascades: if formula A writes to
        a path that formula B depends on, B re-executes after A.

        Entries with _delay use set_timeout for debounce.
        """
        if pathlist is None or not self._formula_registry:
            return

        changed_path = ".".join(str(p) for p in pathlist)
        changed_paths = {changed_path}
        rerun_needed = False

        for entry_id in self._formula_order:
            entry = self._formula_registry[entry_id]
            for v in entry["raw_attrs"].values():
                if is_pointer(v):
                    dep_path = self._resolve_pointer_path(v, entry["node"])
                    if any(
                        dep_path == cp
                        or cp.startswith(dep_path + ".")
                        or dep_path.startswith(cp + ".")
                        for cp in changed_paths
                    ):
                        delay = entry.get("_delay")
                        if delay is not None:
                            self._schedule_delayed_formula(entry_id, entry, delay)
                        else:
                            self._reexecute_formula(entry)
                        rerun_needed = True
                        if entry["path"] is not None:
                            changed_paths.add(entry["path"])
                        break

        if rerun_needed:
            self._rerender()

    def _schedule_delayed_formula(
        self, entry_id: str, entry: dict[str, Any], delay: float,
    ) -> None:
        """Schedule a delayed formula re-execution (debounce).

        Cancels any pending timer for the same entry, then schedules
        a new one. Only the last trigger within the delay window executes.
        """
        old_timer = self._active_timers.get(entry_id)
        if old_timer is not None:
            cancel_timer(old_timer)

        def on_timeout() -> None:
            self._active_timers.pop(entry_id, None)
            self._reexecute_formula(entry)
            self._rerender()

        timer_id = set_timeout(delay, on_timeout)
        self._active_timers[entry_id] = timer_id

    def _on_interval_tick(self, entry_id: str) -> None:
        """Periodic re-execution of a formula/controller with _interval."""
        entry = self._formula_registry.get(entry_id)
        if entry is not None:
            self._reexecute_formula(entry)
            self._rerender()

    def _resolve_pointer_path(self, raw: str, node: BagNode) -> str:
        """Extract absolute data path from a ^pointer string."""
        pointer_info = parse_pointer(raw)
        data_path = pointer_info.path
        if pointer_info.is_relative and hasattr(node, "_resolve_datapath"):
            datapath = node._resolve_datapath()
            rel = data_path[1:]
            data_path = f"{datapath}.{rel}" if datapath else rel
        return data_path

    def _reexecute_formula(self, entry: dict[str, Any]) -> None:
        """Re-execute a single formula/controller with fresh data."""
        node = entry["node"]
        path = entry["path"]
        raw_attrs = entry["raw_attrs"]
        tag = entry["tag"]

        resolved = self._resolve_infra_kwargs(raw_attrs, node, self.data)

        if tag == "data_formula":
            func = resolved.pop("func", None)
            if func is not None and path is not None:
                result = self._call_with_node(func, node, resolved)
                if isinstance(result, dict):
                    result = Bag(source=result)
                self.data.set_item(path, result)
        elif tag == "data_controller":
            func = resolved.pop("func", None)
            if func is not None:
                self._call_with_node(func, node, resolved)

    # -------------------------------------------------------------------------
    # Build walk (source → built materialization)
    # -------------------------------------------------------------------------

    def _build_walk(
        self,
        source: Bag,
        target: Bag,
        data: Bag,
        binding: Any,
        prefix: str = "",
    ) -> None:
        """Recursive walk: two-pass processing.

        Pass 1: Process data_element nodes (side effects on data Bag).
        Pass 2: Materialize normal elements and components in built.

        Args:
            source: The source Bag to compile from.
            target: The built Bag to populate.
            data: Data Bag for ^pointer resolution.
            binding: BindingManager for subscription registration.
            prefix: Path prefix for subscription map keys.
        """
        # Pass 1: process data_element nodes
        for node in source:
            if node.attr.get("_is_data_element"):
                self._process_infra_node(node, data)

        # Pass 2: materialize normal nodes
        for node in source:
            if node.attr.get("_is_data_element"):
                continue

            built_path = f"{prefix}.{node.label}" if prefix else node.label

            binding.unbind_path(built_path)

            value = node.get_value(static=False) if node.resolver is not None else node.static_value

            new_node = target.set_item(
                node.label,
                value if not isinstance(value, Bag) else BuilderBag(builder=type(self)),
                _attributes=dict(node.attr),
                node_tag=node.node_tag,
            )

            self._register_bindings(new_node, built_path, data, binding)

            if isinstance(value, Bag):
                self._build_walk(value, new_node.value, data, binding, prefix=built_path)

    def _process_infra_node(self, node: BagNode, data: Bag) -> None:
        """Process a data_element node during build walk.

        Resolves ^pointers in attributes, then executes the appropriate
        action: data_setter writes value, data_formula computes, data_controller executes.
        Registers formula/controller with ^pointer deps for reactivity.
        Injects _node into callable kwargs if the callable accepts it.
        """
        attrs = dict(node.attr)
        path = attrs.pop("_data_path", None)
        attrs.pop("_is_data_element", None)

        # Resolve relative path
        if path is not None and path.startswith(".") and hasattr(node, "abs_datapath"):
            path = node.abs_datapath(path)

        # Keep raw attrs (with ^pointers) for reactivity registration
        raw_attrs = {k: v for k, v in attrs.items() if not k.startswith("_")}
        resolved = self._resolve_infra_kwargs(attrs, node, data)

        tag = node.node_tag
        if tag == "data_setter":
            value = resolved.get("value")
            if isinstance(value, dict):
                value = Bag(source=value)
            if path is not None:
                data.set_item(path, value)
        elif tag == "data_formula":
            func = resolved.pop("func", None)
            if func is not None and path is not None:
                result = self._call_with_node(func, node, resolved)
                if isinstance(result, dict):
                    result = Bag(source=result)
                data.set_item(path, result)
        elif tag == "data_controller":
            func = resolved.pop("func", None)
            if func is not None:
                self._call_with_node(func, node, resolved)

        # Register formula/controller with pointer deps for reactivity
        if tag in ("data_formula", "data_controller"):
            delay = attrs.get("_delay")
            interval = attrs.get("_interval")
            has_pointer_deps = any(is_pointer(v) for v in raw_attrs.values())
            if has_pointer_deps or interval is not None:
                self._formula_registry[node.label] = {
                    "node": node,
                    "tag": tag,
                    "path": path,
                    "raw_attrs": raw_attrs,
                    "_delay": delay,
                    "_interval": interval,
                }

        # Collect _onBuilt hooks
        on_built = attrs.get("_onBuilt")
        if callable(on_built):
            self._infra_on_built_hooks.append(on_built)

    def _call_with_node(
        self, func: Any, node: BagNode, resolved: dict[str, Any],
    ) -> Any:
        """Call func with resolved kwargs, injecting _node if accepted."""
        sig = inspect.signature(func)
        if "_node" in sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        ):
            resolved["_node"] = node
        return func(**resolved)

    def _resolve_infra_kwargs(
        self, attrs: dict[str, Any], node: BagNode, data: Bag,
    ) -> dict[str, Any]:
        """Resolve ^pointer values in data element attributes."""
        resolved: dict[str, Any] = {}
        for k, v in attrs.items():
            if k.startswith("_"):
                continue
            if is_pointer(v):
                resolved[k] = self._resolve_pointer_from_data(v, node, data)
            else:
                resolved[k] = v
        return resolved

    def _register_bindings(
        self, node: BagNode, built_path: str, data: Bag, binding: Any,
    ) -> None:
        """Register ^pointer subscriptions without resolving values.

        The built node keeps the ^pointer string intact. Resolution happens
        just-in-time during render/compile via _resolve_node.

        Also registers dependencies from computed attributes (callables
        with ^pointer defaults in their parameters).
        """
        pointers = scan_for_pointers(node)

        # Scan callable attributes for ^pointer defaults
        for attr_name, attr_value in node.attr.items():
            if attr_name.startswith("_") or not callable(attr_value):
                continue
            for pointer_raw in self._extract_pointer_defaults(attr_value):
                pointer_info = parse_pointer(pointer_raw)
                pointers.append((pointer_info, f"attr:{attr_name}"))

        if not pointers:
            return

        for pointer_info, location in pointers:
            datapath = ""
            if pointer_info.is_relative and hasattr(node, "_resolve_datapath"):
                datapath = node._resolve_datapath()

            data_path = pointer_info.path
            if pointer_info.is_relative:
                rel = data_path[1:]
                data_path = f"{datapath}.{rel}" if datapath else rel

            data_key = f"{data_path}?{pointer_info.attr}" if pointer_info.attr else data_path
            built_entry = built_path if location == "value" else f"{built_path}?{location[5:]}"

            binding.register(data_key, built_entry)

    def _extract_pointer_defaults(self, func: Any) -> list[str]:
        """Extract ^pointer strings from callable parameter defaults."""
        result: list[str] = []
        sig = inspect.signature(func)
        for param in sig.parameters.values():
            if param.default is not inspect.Parameter.empty and is_pointer(param.default):
                result.append(param.default)
        return result

    def _resolve_pointer(
        self, node: BagNode, pointer_info: Any, data_path: str, data: Bag,
    ) -> Any:
        """Resolve a single ^pointer value from the data Bag."""
        if hasattr(node, "_get_relative_data"):
            return node._get_relative_data(data, pointer_info.raw[1:])

        if pointer_info.attr:
            data_node = data.get_node(data_path)
            return data_node.attr.get(pointer_info.attr) if data_node else None
        return data.get_item(data_path)

    def _resolve_pointer_from_data(
        self, raw: str, node: BagNode, data: Bag,
    ) -> Any:
        """Resolve a ^pointer string to its current value from data.

        Used by _resolve_node for just-in-time resolution during render/compile.
        The built node is NOT modified.
        """
        pointer_info = parse_pointer(raw)

        data_path = pointer_info.path
        if pointer_info.is_relative and hasattr(node, "_resolve_datapath"):
            datapath = node._resolve_datapath()
            rel = data_path[1:]
            data_path = f"{datapath}.{rel}" if datapath else rel

        return self._resolve_pointer(node, pointer_info, data_path, data)

    def _resolve_node(self, node: BagNode, data: Bag) -> dict[str, Any]:
        """Produce a resolved view of a built node.

        Returns a dict with resolved value and attributes. The built node
        is NOT modified — ^pointer strings stay in the built Bag.

        Handles three kinds of attribute values:
        - ^pointer strings: resolved from data
        - callables: defaults inspected for ^pointer deps, called with resolved args
        - plain values: passed through

        Used by renderer/compiler _build_context for just-in-time resolution.
        """
        raw_value = node.get_value(static=True)

        resolved_value = raw_value
        if is_pointer(raw_value):
            resolved_value = self._resolve_pointer_from_data(raw_value, node, data)

        resolved_attrs: dict[str, Any] = {}
        for k, v in node.attr.items():
            if is_pointer(v):
                resolved_attrs[k] = self._resolve_pointer_from_data(v, node, data)
            elif callable(v) and not k.startswith("_"):
                resolved_attrs[k] = self._resolve_computed_attr(v, node, data)
            else:
                resolved_attrs[k] = v

        return {
            "node_value": resolved_value,
            "attrs": resolved_attrs,
            "node": node,
        }

    def _resolve_computed_attr(
        self, func: Any, node: BagNode, data: Bag,
    ) -> Any:
        """Resolve a computed attribute (callable with ^pointer defaults).

        Inspects the callable's parameter defaults for ^pointer strings,
        resolves them from data, and calls the callable with resolved values.
        """
        sig = inspect.signature(func)
        kwargs: dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            if param.default is inspect.Parameter.empty:
                continue
            default = param.default
            if is_pointer(default):
                kwargs[param_name] = self._resolve_pointer_from_data(default, node, data)
            else:
                kwargs[param_name] = default
        return func(**kwargs)

    # -------------------------------------------------------------------------
    # Build / render / rebuild
    # -------------------------------------------------------------------------

    def build(self) -> None:
        """Materialize source → built.

        Two-pass walk: data_elements first, then normal elements.
        After walk, sorts formula by dependency order and calls _onBuilt hooks.
        Does NOT activate reactivity — call ``subscribe()`` separately.
        """
        self._clear_built()
        self._formula_registry = {}
        self._formula_order: list[str] = []
        self._infra_on_built_hooks: list[Any] = []

        self._build_walk(
            self.source, self.built, self.data, self._binding,
        )

        self._formula_order = self._topological_sort_formulas()

        for hook in self._infra_on_built_hooks:
            hook(self)
        self._infra_on_built_hooks = []

    def subscribe(self) -> None:
        """Activate reactive bindings on the built Bag.

        After this call, changes to data are propagated to built nodes
        and output is re-rendered automatically. Formula/controller with
        ^pointer dependencies are re-executed when their sources change.
        Call after ``build()``.
        """
        self._binding.subscribe(self.built, self.data)

        self.source.subscribe(
            "source_watcher",
            delete=self._on_source_deleted,
            insert=self._on_source_inserted,
            update=self._on_source_updated,
        )

        if self._formula_registry:
            self.data.subscribe(
                "formula_watcher",
                any=self._on_formula_data_changed,
            )

        # Start interval timers for formula/controller with _interval
        for entry_id, entry in self._formula_registry.items():
            interval = entry.get("_interval")
            if interval is not None:
                timer_id = set_interval(
                    interval,
                    self._on_interval_tick,
                    entry_id,
                )
                self._active_timers[f"interval:{entry_id}"] = timer_id

        self._auto_compile = True
        self._rerender()

    def render(
        self, built_bag: Bag | None = None, name: str | None = None,
        output: Any = None,
    ) -> str:
        """Render the built Bag to output string.

        Args:
            built_bag: The built Bag to render. Defaults to self.built.
            name: Renderer name. If None and only one renderer, uses that.
            output: Optional destination (file path, stream, etc.).
                Interpretation depends on the renderer implementation.

        Returns:
            Rendered output string.
        """
        if built_bag is None:
            built_bag = self.built
        instance = self._get_output("renderer", self._renderer_instances, name)
        if instance is not None:
            return instance.render(built_bag, output=output)
        # Legacy fallback: _compiler_instance
        if self._compiler_instance is not None:
            if hasattr(self._compiler_instance, "render"):
                return self._compiler_instance.render(built_bag)
            parts = list(self._compiler_instance._walk_compile(built_bag))
            return "\n\n".join(p for p in parts if p)
        raise RuntimeError(
            f"{type(self).__name__} has no renderer or compiler for rendering."
        )

    def compile(
        self, built_bag: Bag | None = None, name: str | None = None,
        target: Any = None,
    ) -> Any:
        """Compile the built Bag into live objects.

        Args:
            built_bag: The built Bag to compile. Defaults to self.built.
            name: Compiler name. If None and only one compiler, uses that.
            target: Optional target (parent widget, container, etc.).
                Interpretation depends on the compiler implementation.

        Returns:
            Compiled output (type depends on compiler).
        """
        if built_bag is None:
            built_bag = self.built
        instance = self._get_output("compiler", self._compiler_instances, name)
        if instance is not None:
            return instance.compile(built_bag, target=target)
        raise RuntimeError(
            f"{type(self).__name__} has no compiler registered."
        )

    def add_renderer(self, name: str, renderer_class: type) -> None:
        """Register a renderer instance at runtime."""
        self._renderer_instances[name] = renderer_class(self)

    def add_compiler(self, name: str, compiler_class: type) -> None:
        """Register a compiler instance at runtime."""
        self._compiler_instances[name] = compiler_class(self)

    def node_by_id(self, node_id: str) -> BagNode:
        """Retrieve a node by its unique node_id.

        Searches this builder's map first, then the source builder's map
        (in standalone mode, the source Bag has its own builder instance).

        Args:
            node_id: The unique identifier assigned via node_id= attribute.

        Returns:
            The BagNode with the given node_id.

        Raises:
            KeyError: If no node with the given node_id exists.
        """
        if node_id in self._node_id_map:
            return self._node_id_map[node_id]
        # In standalone mode, source has its own builder with its own map
        if hasattr(self, "_source_shell"):
            source_builder = self.source._builder
            if source_builder is not None and source_builder is not self and node_id in source_builder._node_id_map:  # noqa: SIM102
                return source_builder._node_id_map[node_id]
        raise KeyError(f"No node with node_id '{node_id}'") from None

    def _get_output(self, kind: str, registry: dict[str, Any], name: str | None) -> Any:
        """Resolve a named or single output instance from a registry."""
        if not registry:
            return None
        if name is None:
            if len(registry) == 1:
                return next(iter(registry.values()))
            raise RuntimeError(f"Multiple {kind}s registered, specify name")
        if name not in registry:
            raise KeyError(f"{kind} '{name}' not found")
        return registry[name]

    def rebuild(self, main: Callable[..., Any] | None = None) -> None:
        """Full rebuild: clear source, optionally re-populate, build.

        Args:
            main: Optional callable(source) to populate the source bag.
                If not provided, only clears and rebuilds from current source.
        """
        self.source.unsubscribe("source_watcher", any=True)
        self._auto_compile = False
        self._clear_source()
        if main is not None:
            main(self.source)
        self.build()

    def _clear_built(self) -> None:
        """Clear the built bag without destroying the shell."""
        self._binding.unbind()
        if self._data is not None:
            self._data.unsubscribe("formula_watcher", any=True)
        for timer_id in self._active_timers.values():
            cancel_timer(timer_id)
        self._active_timers = {}
        self._formula_registry = {}
        self.built.clear()

    def _clear_source(self) -> None:
        """Clear the source bag and the node_id map."""
        self._node_id_map.clear()
        new_root = BuilderBag(builder=type(self))
        self._source_shell.set_item("root", new_root)
        self._bag = self.source

    # -------------------------------------------------------------------------
    # Source change handlers (incremental compile)
    # -------------------------------------------------------------------------

    def _on_source_deleted(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        ind: int | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node is deleted from the source."""
        if not self._auto_compile or node is None:
            return
        # Data elements were never materialized in built
        if node.attr.get("_is_data_element"):
            return
        parts = [str(p) for p in pathlist] if pathlist else []
        parts.append(node.label)
        path = ".".join(parts)
        self._binding.unbind_path(path)
        self.built.del_item(path, _reason="source")
        self._rerender()

    def _on_source_inserted(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        ind: int | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node is inserted into the source."""
        if not self._auto_compile or node is None:
            return

        # Data element: process as infra and re-render
        if node.attr.get("_is_data_element"):
            self._process_infra_node(node, self.data)
            self._rerender()
            return

        parent_path = ".".join(str(p) for p in pathlist) if pathlist else ""

        if parent_path:
            target_bag = self.built.get_item(parent_path)
            if not isinstance(target_bag, Bag):
                return
        else:
            target_bag = self.built

        node_path = f"{parent_path}.{node.label}" if parent_path else node.label

        value = node.get_value(static=False) if node.resolver is not None else node.static_value

        new_node = target_bag.set_item(
            node.label,
            value if not isinstance(value, Bag) else BuilderBag(builder=type(self)),
            _attributes=dict(node.attr),
            node_tag=node.node_tag,
            node_position=ind,
            _reason="source",
        )

        self._register_bindings(
            new_node, node_path, self.data, self._binding,
        )

        if isinstance(value, Bag):
            self._build_walk(
                value, new_node.value, self.data, self._binding, prefix=node_path,
            )

        self._rerender()

    def _on_source_updated(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node in the source is updated (value or attributes)."""
        if not self._auto_compile or pathlist is None:
            return

        # Data element: re-process and re-render
        if node is not None and node.attr.get("_is_data_element"):
            self._process_infra_node(node, self.data)
            self._rerender()
            return

        path = ".".join(str(p) for p in pathlist)
        built_node = self.built.get_node(path)
        if built_node is None:
            return

        if evt == "upd_value":
            value = node.get_value(static=False) if node.resolver is not None else node.static_value

            self._binding.unbind_path(path)

            if isinstance(value, Bag):
                built_node.set_value(BuilderBag(builder=type(self)), _reason="source")
                self._register_bindings(
                    built_node, path, self.data, self._binding,
                )
                self._build_walk(
                    value, built_node.value, self.data, self._binding, prefix=path,
                )
            else:
                built_node.set_value(value, _reason="source")
                self._register_bindings(
                    built_node, path, self.data, self._binding,
                )

        elif evt == "upd_attrs":
            if node is not None:
                built_node.set_attr(dict(node.attr))
                self._binding.unbind_path(path)
                self._register_bindings(
                    built_node, path, self.data, self._binding,
                )

        self._rerender()

    # -------------------------------------------------------------------------
    # Bag delegation
    # -------------------------------------------------------------------------

    def _bag_call(self, bag: Bag, name: str) -> Any:
        """Return callable that creates a schema element in the bag.

        Precondition: name is in self._schema.
        """
        info = self._get_schema_info(name)
        if info.get("is_data_element"):
            handler = getattr(self, info["handler_name"])

            def data_element_call(*args: Any, **kwargs: Any) -> None:
                path, attrs_dict = handler(*args, **kwargs)
                return self._add_data_element(bag, name, path, attrs_dict)

            return data_element_call

        handler = self.__getattr__(name)
        return lambda node_value=None, node_label=None, node_position=None, **attr: handler(
            bag,
            _tag=name,
            node_value=node_value,
            node_label=node_label,
            node_position=node_position,
            **attr,
        )

    # -------------------------------------------------------------------------
    # Element dispatch
    # -------------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        """Look up tag in _schema and return handler with validation."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        def wrapper(destination_bag: Bag, *args: Any, node_tag: str = name, **kwargs: Any) -> Any:
            try:
                info = self._get_schema_info(node_tag)
            except KeyError as err:
                raise AttributeError(f"'{type(self).__name__}' has no element '{node_tag}'") from err

            # Data element: multi-positional args, bypass validation
            if info.get("is_data_element"):
                handler = getattr(self, info["handler_name"])
                path, attrs_dict = handler(*args, **kwargs)
                return self._add_data_element(destination_bag, node_tag, path, attrs_dict)

            # Validazione sui kwargs originali, PRIMA del method
            node_value = args[0] if args else kwargs.get("node_value")
            self._validate_call_args(info, node_value, kwargs)

            # Check if this is a component
            if info.get("is_component"):
                return self._handle_component(destination_bag, info, node_tag, kwargs)

            # Element: no adapter, registra direttamente con kwargs originali
            kwargs.pop("node_value", None)
            return self._add_element(destination_bag, node_value, node_tag=node_tag, **kwargs)

        return wrapper

    def _handle_component(
        self,
        destination_bag: Bag,
        info: dict,
        node_tag: str,
        kwargs: dict,
    ) -> Any:
        """Handle component invocation - lazy registration with resolver.

        Registers the component node with a ComponentResolver. The handler
        body is NOT called here — it will be called lazily when the node
        is accessed with static=False (during expand or compile).

        Always returns a ComponentProxy that delegates to destination_bag.
        If the component has named slots, the proxy also provides access
        to slot Bags via attribute access.

        Args:
            destination_bag: The parent Bag where component will be added.
            info: Schema info for the component.
            node_tag: The tag name for the component.
            kwargs: Arguments passed to the component (stored as attributes).

        Returns:
            ComponentProxy wrapping destination_bag (and optional slot Bags).
        """
        from .builder_bag import BuilderBag
        from .component_proxy import ComponentProxy
        from .component_resolver import ComponentResolver

        # Extract internal kwargs that need special handling
        kwargs.pop("node_value", None)
        node_label = kwargs.pop("node_label", None)
        node_position = kwargs.pop("node_position", None)

        # Register node with kwargs as attributes, no expansion
        node = self._add_element(
            destination_bag,
            node_value=None,
            node_tag=node_tag,
            node_label=node_label,
            node_position=node_position,
            **kwargs,
        )

        # Attach resolver for lazy expansion
        handler_name = info.get("handler_name")
        handler = getattr(self, handler_name) if handler_name else None
        builder_class = info.get("component_builder") or type(self)
        based_on = info.get("based_on")
        slot_names = info.get("slots") or []

        # Create slot Bags (empty, to be populated at recipe time)
        slots = {name: BuilderBag(builder=builder_class) for name in slot_names}

        resolver = ComponentResolver(
            handler=handler,
            builder_class=builder_class,
            based_on=based_on,
            builder=self,
            slots=slots if slots else None,
        )
        node.resolver = resolver

        return ComponentProxy(destination_bag, slots)

    def _add_element(
        self,
        build_where: Bag,
        node_value: Any = None,
        node_label: str | None = None,
        node_tag: str = "",
        **attr: Any,
    ) -> BagNode:
        """Add an element node to the bag.

        Called by the wrapper after optional adapter transformation.

        Args:
            build_where: The destination Bag where the node will be created.
            node_value: Node content (positional). Becomes node.value.
            node_label: Optional explicit label for the node.
            node_tag: The tag name for the element.
            **attr: Node attributes.
        """
        return self._child(build_where, node_tag, node_value, node_label=node_label, **attr)

    def _add_data_element(
        self, build_where: Bag, node_tag: str,
        path: str | None, attrs_dict: dict[str, Any],
    ) -> None:
        """Add a data element node to the source bag.

        Not materialized in built. Processed as side effect during build walk.
        Bypasses _child() validation — data elements are transparent.
        """
        label = self._auto_label(build_where, node_tag)
        build_where.set_item(
            label, None,
            _attributes={
                **attrs_dict,
                "_is_data_element": True,
                "_data_path": path,
            },
            node_tag=node_tag,
        )

    def _child(
        self,
        build_where: Bag,
        node_tag: str,
        node_value: Any = None,
        node_label: str | None = None,
        node_position: str | int | None = None,
        **attr: Any,
    ) -> BagNode:
        """Create a child node in the target Bag with validation.

        Raises ValueError if validation fails, KeyError if parent tag not in schema.
        """
        parent_node = build_where._parent_node
        if parent_node and parent_node.node_tag:
            parent_info = self._get_schema_info(parent_node.node_tag)
            self._accept_child(parent_node, parent_info, node_tag, node_position)

        child_info = self._get_schema_info(node_tag)
        self._validate_parent_tags(child_info, parent_node)

        # Extract node_id before passing attrs to set_item
        node_id = attr.pop("node_id", None)

        node_label = node_label or self._auto_label(build_where, node_tag)
        child_node = build_where.set_item(
            node_label, node_value, _attributes=dict(attr),
            node_position=node_position, node_tag=node_tag,
        )

        # Register node_id if provided
        if node_id is not None:
            if hasattr(self, "_node_id_map"):
                if node_id in self._node_id_map:
                    raise ValueError(
                        f"Duplicate node_id '{node_id}': already assigned to "
                        f"node '{self._node_id_map[node_id].label}'"
                    )
                self._node_id_map[node_id] = child_node
            child_node.set_attr({"node_id": node_id}, trigger=False)

        if parent_node and parent_node.node_tag:
            self._validate_sub_tags(parent_node, parent_info)

        self._validate_sub_tags(child_node, child_info)

        return child_node

    def _auto_label(self, build_where: Bag, node_tag: str) -> str:
        """Generate unique label for a node: tag_0, tag_1, ..."""
        n = 0
        while f"{node_tag}_{n}" in build_where._nodes:
            n += 1
        return f"{node_tag}_{n}"

    def _validate_call_args(
        self,
        info: dict,
        node_value: Any,
        attr: dict[str, Any],
    ) -> None:
        """Validate attributes and node_value. Raises ValueError if invalid."""
        call_args_validations = info.get("call_args_validations")
        if not call_args_validations:
            return

        errors: list[str] = []
        all_args = dict(attr)
        if node_value is not None:
            all_args["node_value"] = node_value

        for attr_name, (base_type, validators, default) in call_args_validations.items():
            attr_value = all_args.get(attr_name)

            # Required check
            if default is inspect.Parameter.empty and attr_value is None:
                errors.append(f"required attribute '{attr_name}' is missing")
                continue

            if attr_value is None:
                continue

            # Type check
            if not _check_type(attr_value, base_type):
                errors.append(
                    f"'{attr_name}': expected {base_type}, got {type(attr_value).__name__}"
                )
                continue

            # Validator checks (Regex, Range, etc.)
            for v in validators:
                try:
                    v(attr_value)
                except Exception as e:
                    errors.append(f"'{attr_name}': {e}")

        if errors:
            raise ValueError("Validation failed: " + "; ".join(errors))

    def _validate_children_tags(
        self,
        node_tag: str,
        sub_tags_compiled: dict[str, tuple[int, int]] | str,
        children_tags: list[str],
    ) -> list[str]:
        """Validate a list of child tags against sub_tags spec.

        Args:
            node_tag: Tag of parent node (for error messages)
            sub_tags_compiled: Compiled sub_tags: "*" for any, or dict {tag: (min, max)}
            children_tags: List of child tags to validate

        Returns:
            List of invalid_reasons (missing required tags)

        Raises:
            ValueError: if tag not allowed or max exceeded
        """
        # Wildcard "*" accepts any children - no validation needed
        if sub_tags_compiled == "*":
            return []

        bounds = {tag: list(minmax) for tag, minmax in sub_tags_compiled.items()}
        for tag in children_tags:
            minmax = bounds.get(tag)
            if minmax is None:
                raise ValueError(f"'{tag}' not allowed as child of '{node_tag}'")
            minmax[1] -= 1
            if minmax[1] < 0:
                raise ValueError(f"Too many '{tag}' in '{node_tag}'")
            minmax[0] -= 1

        # Warnings for missing required elements (min > 0 after decrement)
        return [tag for tag, (n_min, _) in bounds.items() if n_min > 0]

    def _validate_sub_tags(self, node: BagNode, info: dict) -> None:
        """Validate sub_tags constraints on node's existing children.

        Gets children_tags from node's actual children, calls _validate_children_tags,
        and sets node._invalid_reasons.

        Args:
            node: The node to validate.
            info: Schema info dict from get_schema_info().
        """
        node_tag = node.node_tag
        if not node_tag:
            node._invalid_reasons = []
            return

        sub_tags_compiled = info.get("sub_tags_compiled")
        if sub_tags_compiled is None:
            node._invalid_reasons = []
            return

        # Wildcard "*" accepts any children - no validation needed
        if sub_tags_compiled == "*":
            node._invalid_reasons = []
            return

        children_tags = [
            n.node_tag for n in node.value.nodes
            if not n.attr.get("_is_data_element")
        ] if isinstance(node.value, Bag) else []

        node._invalid_reasons = self._validate_children_tags(
            node_tag, sub_tags_compiled, children_tags
        )

    def _accept_child(
        self,
        target_node: BagNode,
        info: dict,
        child_tag: str,
        node_position: str | int | None,
    ) -> None:
        """Check if target_node can accept child_tag at node_position.

        Builds children_tags = current tags + new tag, calls _validate_children_tags.
        Raises ValueError if not valid.
        """
        sub_tags_compiled = info.get("sub_tags_compiled")
        if sub_tags_compiled is None:
            return

        # Wildcard "*" accepts any children - no validation needed
        if sub_tags_compiled == "*":
            return

        # Build children_tags = current + new (excluding data elements)
        children_tags = (
            [n.node_tag for n in target_node.value.nodes
             if not n.attr.get("_is_data_element")]
            if isinstance(target_node.value, Bag) else []
        )

        # Insert new tag at correct position
        idx = (
            target_node.value._nodes._parse_position(node_position)
            if isinstance(target_node.value, Bag)
            else 0
        )
        children_tags.insert(idx, child_tag)

        self._validate_children_tags(target_node.node_tag, sub_tags_compiled, children_tags)

    def _validate_parent_tags(
        self,
        child_info: dict,
        parent_node: BagNode | None,
    ) -> None:
        """Validate that child can be placed in parent based on parent_tags.

        Args:
            child_info: Schema info for the child element.
            parent_node: The parent node (None if adding to root).

        Raises:
            ValueError: If parent_tags is specified and parent is not in the list.
        """
        parent_tags_compiled = child_info.get("parent_tags_compiled")
        if parent_tags_compiled is None:
            return

        parent_tag = parent_node.node_tag if parent_node else None
        if parent_tag not in parent_tags_compiled:
            valid_parents = ", ".join(sorted(parent_tags_compiled))
            raise ValueError(
                f"Element cannot be placed here: parent_tags requires one of [{valid_parents}], "
                f"but parent is '{parent_tag or 'root'}'"
            )

    def _command_on_node(
        self,
        node: BagNode,
        child_tag: str,
        node_position: str | int | None = None,
        node_value: Any = None,
        **attrs: Any,
    ) -> Any:
        """Add a child to a node.

        Uses _bag_call for schema elements (handles components and tag renames).
        Falls back to self._child() for unknown tags (provides validation errors).
        """
        from .builder_bag import BuilderBag

        if not isinstance(node.value, Bag):
            node.value = BuilderBag()
            node.value.builder = self

        if child_tag in self._schema:
            info = self._get_schema_info(child_tag)
            if info.get("is_data_element"):
                handler = getattr(self, info["handler_name"])
                args = (node_value,) if node_value is not None else ()
                path, attrs_dict = handler(*args, **attrs)
                return self._add_data_element(node.value, child_tag, path, attrs_dict)
            callable_handler = self._bag_call(node.value, child_tag)
            return callable_handler(
                node_value=node_value,
                node_position=node_position,
                **attrs,
            )

        # Tag not in schema: use _child() which will validate and raise
        return self._child(
            node.value,
            child_tag,
            node_value=node_value,
            node_position=node_position,
            **attrs,
        )

    # -------------------------------------------------------------------------
    # Schema access
    # -------------------------------------------------------------------------

    def __contains__(self, name: str) -> bool:
        """Check if element exists in schema."""
        return self._schema.get_node(name) is not None

    def _get_schema_info(self, name: str) -> dict:
        """Return info dict for an element.

        Returns dict with keys:
            - adapter_name: str | None
            - sub_tags: str | None
            - sub_tags_compiled: dict[str, tuple[int, int]] | None
            - call_args_validations: dict | None

        Raises KeyError if element not in schema.
        """
        schema_node = self._schema.get_node(name)
        if schema_node is None:
            raise KeyError(f"Element '{name}' not found in schema")

        cached = schema_node.attr.get("_cached_info")  # type: ignore[union-attr]
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        result = dict(schema_node.attr)  # type: ignore[union-attr]
        inherits_from = result.pop("inherits_from", None)

        if inherits_from:
            # Support multiple inheritance: "alfa,beta" -> ["alfa", "beta"]
            # Parents are processed left-to-right, later parents override earlier ones
            parents = [p.strip() for p in inherits_from.split(",")]
            for parent in parents:
                abstract_attrs = self._schema.get_attr(parent)
                if abstract_attrs:
                    for k, v in abstract_attrs.items():
                        # Skip inherits_from from abstract - don't propagate it
                        if k == "inherits_from":
                            continue
                        if k == "_meta":
                            # Merge meta: abstract base + element overrides
                            inherited = v or {}
                            current = result.get("_meta") or {}
                            result["_meta"] = {**inherited, **current}
                        elif k not in result or not result[k]:
                            result[k] = v

        sub_tags = result.get("sub_tags")
        if sub_tags is not None:
            result["sub_tags_compiled"] = _parse_sub_tags_spec(sub_tags)

        parent_tags = result.get("parent_tags")
        if parent_tags is not None:
            result["parent_tags_compiled"] = _parse_parent_tags_spec(parent_tags)

        schema_node.attr["_cached_info"] = result  # type: ignore[union-attr]
        return result

    def __iter__(self):
        """Iterate over schema nodes."""
        return iter(self._schema)

    def __repr__(self) -> str:
        """Show builder schema summary."""
        count = sum(1 for _ in self)
        return f"<{type(self).__name__} ({count} elements)>"

    def __str__(self) -> str:
        """Show schema structure."""
        return str(self._schema)

    # -------------------------------------------------------------------------
    # Validation check
    # -------------------------------------------------------------------------

    def _check(self, bag: Bag | None = None) -> list[tuple[str, BagNode, list[str]]]:
        """Return report of invalid nodes."""
        if bag is None:
            bag = self._bag
        invalid_nodes: list[tuple[str, BagNode, list[str]]] = []
        self._walk_check(bag, "", invalid_nodes)
        return invalid_nodes

    def _walk_check(
        self,
        bag: Bag,
        path: str,
        invalid_nodes: list[tuple[str, BagNode, list[str]]],
    ) -> None:
        """Walk tree collecting invalid nodes."""
        for node in bag:
            node_path = f"{path}.{node.label}" if path else node.label

            if node._invalid_reasons:
                invalid_nodes.append((node_path, node, node._invalid_reasons.copy()))

            node_value = node.get_value(static=True)
            if isinstance(node_value, Bag):
                self._walk_check(node_value, node_path, invalid_nodes)

    # -------------------------------------------------------------------------
    # Compiler access
    # -------------------------------------------------------------------------

    @property
    def _compiler(self) -> Any:
        """Return compiler instance for this builder.

        Requires _compiler_class to be defined on the builder subclass.

        Raises:
            ValueError: If _compiler_class is not defined.
        """
        if self._compiler_class is None:
            raise ValueError(f"{type(self).__name__} has no _compiler_class defined")
        return self._compiler_class(self)

    def _compile(self, **kwargs: Any) -> Any:
        """Compile the bag via the compiler, then render to output string.

        If _compiler_class is defined, compiles source into a target bag
        and then renders it using the compiler's render method.

        Without _compiler_class, falls back to XML/JSON serialization (string).

        Args:
            **kwargs: Extra parameters. 'destination' writes output to file.
                'format' selects legacy format ('xml' or 'json').

        Returns:
            Rendered output string.
        """
        if self._compiler_class is not None:
            from .binding import BindingManager
            from .builder_bag import BuilderBag

            compiler = self._compiler
            target = BuilderBag(builder=type(self))
            data = kwargs.pop("data", None) or Bag()
            binding = kwargs.pop("binding", None) or BindingManager()
            self._build_walk(self._bag, target, data, binding)

            destination = kwargs.get("destination")
            if hasattr(compiler, "render"):
                result = compiler.render(target)
            else:
                parts = list(compiler._walk_compile(target))
                result = "\n".join(p for p in parts if p)

            if destination is not None:
                from pathlib import Path
                Path(destination).write_text(result)

            return result
        format_ = kwargs.get("format", "xml")
        if format_ == "xml":
            return self._bag.to_xml()
        elif format_ == "json":
            return self._bag.to_tytx(transport="json")  # type: ignore[return-value]
        else:
            raise ValueError(f"Unknown format: {format_}")

    # -------------------------------------------------------------------------
    # Schema documentation
    # -------------------------------------------------------------------------

    def _schema_to_md(self, title: str | None = None) -> str:
        """Generate Markdown documentation for the builder schema.

        Creates a formatted Markdown document with tables for abstract
        and concrete elements, including all schema information.

        Args:
            title: Optional title for the document. Defaults to class name.

        Returns:
            Markdown string with schema documentation.
        """
        from .builders.markdown import MarkdownBuilder

        md_builder = MarkdownBuilder()
        doc = md_builder.source
        builder_name = title or type(self).__name__

        doc.h1(f"Schema: {builder_name}")

        # Collect abstracts and elements
        abstracts: list[tuple[str, dict]] = []
        elements: list[tuple[str, dict]] = []

        for node in self._schema:
            name = node.label
            info = self._get_schema_info(name)
            if name.startswith("@"):
                abstracts.append((name[1:], info))
            else:
                elements.append((name, info))

        # Abstract elements section
        if abstracts:
            doc.h2("Abstract Elements")
            table = doc.table()
            header = table.tr()
            header.th("Name")
            header.th("Sub Tags")
            header.th("Documentation")

            for name, info in sorted(abstracts):
                row = table.tr()
                row.td(f"`@{name}`")
                row.td(f"`{info.get('sub_tags') or '-'}`")
                row.td(info.get("documentation") or "-")

        # Concrete elements section
        if elements:
            doc.h2("Elements")
            table = doc.table()
            header = table.tr()
            header.th("Name")
            header.th("Inherits")
            header.th("Sub Tags")
            header.th("Call Args")
            header.th("Compile")
            header.th("Documentation")

            for name, info in sorted(elements):
                row = table.tr()
                row.td(f"`{name}`")

                inherits = info.get("inherits_from")
                row.td(f"`{inherits}`" if inherits else "-")

                sub_tags = info.get("sub_tags")
                row.td(f"`{sub_tags}`" if sub_tags else "-")

                call_args = info.get("call_args_validations")
                if call_args:
                    args_str = ", ".join(call_args.keys())
                    row.td(f"`{args_str}`")
                else:
                    row.td("-")

                meta = info.get("_meta") or {}
                meta_parts = []
                if "template" in meta:
                    tmpl = meta["template"].replace("`", "\\`")
                    tmpl = tmpl.replace("\n", "\\n")
                    meta_parts.append(f"template: {tmpl}")
                if "callback" in meta:
                    meta_parts.append(f"callback: {meta['callback']}")
                for k, v in meta.items():
                    if k not in ("template", "callback"):
                        meta_parts.append(f"{k}: {v}")
                if meta_parts:
                    row.td("`" + ", ".join(meta_parts) + "`")
                else:
                    row.td("-")

                row.td(info.get("documentation") or "-")

        md_builder.build()
        return md_builder.render()

    # -------------------------------------------------------------------------
    # Value rendering (for compile)
    # -------------------------------------------------------------------------

    def _render_value(self, node: BagNode) -> str:
        """Render node value applying format and template transformations.

        Applies transformations in order:
        1. value_format (node attr) - format the raw value
        2. value_template (node attr) - apply runtime template
        3. _meta callback - call method to modify context in place
        4. _meta format - format from decorator
        5. _meta template - structural template from decorator

        Template placeholders available:
        - {node_value}: the node value
        - {node_label}: the node label
        - {attr_name}: any node attribute (e.g., {lang}, {href})

        Args:
            node: The BagNode to render.

        Returns:
            Rendered string value.
        """
        node_value = node.get_value(static=True)
        node_value = "" if node_value is None else str(node_value)

        # Build template context: node_value, node_label, and all attributes
        # Start with default values from schema for optional parameters
        tag = node.node_tag or node.label
        info = self._get_schema_info(tag)
        call_args = info.get("call_args_validations") or {}
        template_ctx: dict[str, Any] = {}
        for param_name, (default, _validators, _type) in call_args.items():
            if default is not None:
                template_ctx[param_name] = default
        # Override with actual node attributes
        template_ctx.update(node.attr)
        template_ctx["node_value"] = node_value
        template_ctx["node_label"] = node.label
        template_ctx["_node"] = node  # For callbacks needing full node access

        # 1. value_format from node attr (runtime)
        value_format = node.attr.get("value_format")
        if value_format:
            try:
                node_value = value_format.format(node_value)
                template_ctx["node_value"] = node_value
            except (ValueError, KeyError):
                pass

        # 2. value_template from node attr (runtime)
        value_template = node.attr.get("value_template")
        if value_template:
            node_value = value_template.format(**template_ctx)
            template_ctx["node_value"] = node_value

        # 3-5. _meta callback, format, template from schema
        meta = info.get("_meta") or {}

        # 3. callback - call method to modify context in place
        callback = meta.get("callback")
        if callback:
            method = getattr(self, callback)
            method(template_ctx)
            node_value = template_ctx["node_value"]

        # 4. format from _meta
        fmt = meta.get("format")
        if fmt:
            try:
                node_value = fmt.format(node_value)
                template_ctx["node_value"] = node_value
            except (ValueError, KeyError):
                pass

        # 5. template from _meta
        template = meta.get("template")
        if template:
            node_value = template.format(**template_ctx)

        return node_value

    # -------------------------------------------------------------------------
    # Call args validation (internal)
    # -------------------------------------------------------------------------

    def _get_call_args_validations(self, tag: str) -> dict[str, tuple[Any, list, Any]] | None:
        """Return attribute spec for a tag from schema."""
        schema_node = self._schema.node(tag)
        if schema_node is None:
            return None
        return schema_node.attr.get("call_args_validations")


# =============================================================================
# Type hint parsing utilities (internal)
# =============================================================================


def _split_annotated(tp: Any) -> tuple[Any, list]:
    """Split Annotated type into base type and validators.

    Handles Optional[Annotated[T, ...]] which appears as Union[Annotated[T, ...], None].
    """
    if get_origin(tp) is Annotated:
        base, *meta = get_args(tp)
        validators = [m for m in meta if callable(m)]
        return base, validators

    # Handle Optional[Annotated[...]] -> Union[Annotated[...], None]
    from typing import Union

    if get_origin(tp) is Union:
        args = get_args(tp)
        # Check if it's Optional (Union with NoneType)
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            inner = non_none_args[0]
            if get_origin(inner) is Annotated:
                base, *meta = get_args(inner)
                validators = [m for m in meta if callable(m)]
                return base, validators

    return tp, []


def _check_type(value: Any, tp: Any) -> bool:
    """Check if value matches the type annotation."""
    tp, _ = _split_annotated(tp)

    origin = get_origin(tp)
    args = get_args(tp)

    if tp is Any:
        return True

    if tp is type(None):
        return value is None

    if origin is Literal:
        return value in args

    if origin is types.UnionType:
        return any(_check_type(value, t) for t in args)

    try:
        from typing import Union

        if origin is Union:
            return any(_check_type(value, t) for t in args)
    except ImportError:
        pass

    if origin is None:
        try:
            return isinstance(value, tp)
        except TypeError:
            return True

    if origin is list:
        if not isinstance(value, list):
            return False
        if not args:
            return True
        t_item = args[0]
        return all(_check_type(v, t_item) for v in value)

    if origin is dict:
        if not isinstance(value, dict):
            return False
        if not args:
            return True
        k_t, v_t = args[0], args[1] if len(args) > 1 else Any
        return all(_check_type(k, k_t) and _check_type(v, v_t) for k, v in value.items())

    if origin is tuple:
        if not isinstance(value, tuple):
            return False
        if not args:
            return True
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_check_type(v, args[0]) for v in value)
        return len(value) == len(args) and all(
            _check_type(v, t) for v, t in zip(value, args, strict=True)
        )

    if origin is set:
        if not isinstance(value, set):
            return False
        if not args:
            return True
        t_item = args[0]
        return all(_check_type(v, t_item) for v in value)

    try:
        return isinstance(value, origin)
    except TypeError:
        return True


def _extract_validators_from_signature(fn: Callable) -> dict[str, tuple[Any, list, Any]]:
    """Extract type hints with validators from function signature."""
    skip_params = {
        "self",
        "build_where",
        "node_tag",
        "node_label",
        "node_position",
        "component",  # first param of @component methods
        "comp",  # short form for component param
    }

    try:
        hints = get_type_hints(fn, include_extras=True)
    except Exception:
        return {}

    result = {}
    sig = inspect.signature(fn)

    for name, param in sig.parameters.items():
        if name in skip_params:
            continue
        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue

        tp = hints.get(name)
        if tp is None:
            continue

        base, validators = _split_annotated(tp)
        result[name] = (base, validators, param.default)

    return result


# =============================================================================
# Sub-tags and parent-tags validation utilities (internal)
# =============================================================================


def _parse_parent_tags_spec(spec: str) -> set[str]:
    """Parse parent_tags spec into set of valid parent tag names.

    Simple comma-separated list of tag names (no cardinality).

    Args:
        spec: Comma-separated list of tag names, e.g. "div, span, section".

    Returns:
        Set of valid parent tag names.
    """
    return {tag.strip() for tag in spec.split(",") if tag.strip()}


def _parse_sub_tags_spec(spec: str) -> dict[str, tuple[int, int]] | str:
    """Parse sub_tags spec into dict of {tag: (min, max)} or "*" for any.

    Semantics:
        ""       -> leaf element (no children allowed) - returns empty dict
        "*"      -> accepts any children (no validation) - returns "*"
        "foo"    -> accepts only "foo" children

    Cardinality syntax:
        foo      -> any number 0..N (min=0, max=sys.maxsize)
        foo[1]   -> exactly 1 (min=1, max=1)
        foo[3]   -> exactly 3 (min=3, max=3)
        foo[0:]  -> 0 or more (min=0, max=sys.maxsize)
        foo[:2]  -> 0 to 2 (min=0, max=2)
        foo[1:3] -> 1 to 3 (min=1, max=3)
        foo[]    -> ERROR (invalid syntax)

    Returns:
        "*" if spec is "*" (accepts any children)
        dict of {tag: (min, max)} otherwise
    """
    # Handle wildcard - accepts any children
    if spec == "*":
        return "*"

    result: dict[str, tuple[int, int]] = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        # Try [min:max] format first
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\[(\d*):(\d*)\]$", item)
        if match:
            tag = match.group(1)
            min_val = int(match.group(2)) if match.group(2) else 0
            max_val = int(match.group(3)) if match.group(3) else sys.maxsize
            result[tag] = (min_val, max_val)
            continue
        # Try [n] format (exactly n)
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\[(\d+)\]$", item)
        if match:
            tag = match.group(1)
            n = int(match.group(2))
            result[tag] = (n, n)
            continue
        # Check for invalid [] format
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\[\]$", item)
        if match:
            raise ValueError(
                f"Invalid sub_tags syntax: '{item}' - use 'foo' for 0..N or 'foo[n]' for exact count"
            )
        # Plain tag name (0..N)
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)$", item)
        if match:
            tag = match.group(1)
            result[tag] = (0, sys.maxsize)
    return result


def _decorated_method_info(
    name: str, obj: Any,
) -> tuple[list[str], str | None, Any, dict]:
    """Build (tag_list, method_name, obj, decorator_info) for a decorated method."""
    decorator_info = obj._decorator
    if decorator_info.get("abstract"):
        return [f"@{name}"], None, obj, decorator_info
    elif decorator_info.get("data_element"):
        tag_list: list[str] = [] if name.startswith("_") else [name]
        tags_raw = decorator_info.get("tags")
        if tags_raw:
            if isinstance(tags_raw, str):
                tag_list.extend(t.strip() for t in tags_raw.split(",") if t.strip())
            else:
                tag_list.extend(tags_raw)
        handler_name = f"_dtel_{tag_list[0]}"
        return tag_list, handler_name, obj, decorator_info
    elif decorator_info.get("component"):
        tag_list: list[str] = [] if name.startswith("_") else [name]
        tags_raw = decorator_info.get("tags")
        if tags_raw:
            if isinstance(tags_raw, str):
                tag_list.extend(t.strip() for t in tags_raw.split(",") if t.strip())
            else:
                tag_list.extend(tags_raw)
        handler_name = f"_comp_{tag_list[0]}"
        return tag_list, handler_name, obj, decorator_info
    else:
        tag_list = [] if name.startswith("_") else [name]
        tags_raw = decorator_info.get("tags")
        if tags_raw:
            if isinstance(tags_raw, str):
                tag_list.extend(t.strip() for t in tags_raw.split(",") if t.strip())
            else:
                tag_list.extend(tags_raw)
        return tag_list, None, obj, decorator_info


def _pop_decorated_methods(cls: type):
    """Remove and yield decorated methods from cls and its mixin bases.

    Collects @element, @abstract, and @component methods from:
    1. The class itself (cls.__dict__) — removed with delattr
    2. Mixin bases in MRO that are not BagBuilderBase subclasses

    Methods defined directly on cls take priority over mixin methods.
    Mixin methods are NOT removed from their defining class.
    """
    seen: set[str] = set()

    for name, obj in list(cls.__dict__.items()):
        if hasattr(obj, "_decorator"):
            seen.add(name)
            delattr(cls, name)
            yield _decorated_method_info(name, obj)

    for base in cls.__mro__:
        if base is cls or base is object:
            continue
        if base is BagBuilderBase:
            # Collect @data_element methods from BagBuilderBase
            for name, obj in list(base.__dict__.items()):
                if name in seen:
                    continue
                if hasattr(obj, "_decorator") and obj._decorator.get("data_element"):
                    seen.add(name)
                    yield _decorated_method_info(name, obj)
            continue
        if issubclass(base, BagBuilderBase):
            continue
        for name, obj in list(base.__dict__.items()):
            if name in seen:
                continue
            if hasattr(obj, "_decorator"):
                seen.add(name)
                yield _decorated_method_info(name, obj)


# =============================================================================
# SchemaBuilder
# =============================================================================


class SchemaBuilder(BagBuilderBase):
    """Builder for creating builder schemas programmatically.

    Use SchemaBuilder to define schemas at runtime instead of using decorators.
    Creates schema nodes with the structure expected by BagBuilderBase.

    Note: SchemaBuilder cannot define @component - components require code
    handlers and must be defined using the @component decorator.

    Schema conventions:
        - Elements: stored by name (e.g., 'div', 'span')
        - Abstracts: prefixed with '@' (e.g., '@flow', '@phrasing')
        - Use inherits_from='@abstract' to inherit sub_tags

    Usage:
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item('@flow', sub_tags='p,span')
        schema.builder.item('div', inherits_from='@flow')
        schema.builder.item('li', parent_tags='ul,ol')  # li only inside ul or ol
        schema.builder.item('br', sub_tags='')  # void element
        schema.builder._compile('schema.msgpack')
    """

    def item(
        self,
        name: str,
        sub_tags: str | None = None,
        parent_tags: str | None = None,
        inherits_from: str | None = None,
        call_args_validations: dict[str, tuple[Any, list, Any]] | None = None,
        _meta: dict[str, Any] | None = None,
        documentation: str | None = None,
    ) -> BagNode:
        """Define a schema item (element definition).

        Args:
            name: Element name to define (e.g., 'div', '@flow').
            sub_tags: Valid child tags with cardinality syntax.
            parent_tags: Comma-separated list of valid parent tags for this element.
            inherits_from: Abstract element name to inherit sub_tags from.
            call_args_validations: Validation spec for element attributes.
            _meta: Dict of metadata for renderers/compilers.
            documentation: Documentation string for the element.

        Returns:
            The created BagNode.
        """
        attrs: dict[str, Any] = {}
        if sub_tags is not None:
            attrs["sub_tags"] = sub_tags
        if parent_tags is not None:
            attrs["parent_tags"] = parent_tags
        if inherits_from is not None:
            attrs["inherits_from"] = inherits_from
        if call_args_validations is not None:
            attrs["call_args_validations"] = call_args_validations
        if _meta:
            attrs["_meta"] = _meta
        if documentation is not None:
            attrs["documentation"] = documentation

        return self._bag.set_item(name, None, **attrs)

    def _compile(self, destination: str | Path) -> None:  # type: ignore[override]
        """Save schema to MessagePack file for later loading by builders.

        Args:
            destination: Path to the output .msgpack file.
        """
        msgpack_data = self._bag.to_tytx(transport="msgpack")
        Path(destination).write_bytes(msgpack_data)  # type: ignore[arg-type]
