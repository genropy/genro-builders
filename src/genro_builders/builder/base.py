# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderBase — grammar base class for Bag builders.

A builder declares the grammar of a dialect via decorators
(@element, @abstract) and the schema of valid tag placements
(sub_tags, parent_tags). Sub-builders and data-elements are ordinary
@element marked in their ``_meta`` (no dedicated decorator). The three data-elements
(data_setter / data_formula / data_controller) are ordinary @element
declared on this base and marked ``_meta['data_element']``. A builder
renders itself: it owns its source (under the ``main`` segment of a
wrapper root) and the create/render phases. Data, reactivity and
node_id lookup across mounted builders live on the BuilderHandler.

Exports:
    BuilderBase: Base class for all builders.
"""

from __future__ import annotations

import contextlib
import json
from abc import ABC
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from genro_bag import Bag

from ..renderer.xml import XmlRenderer
from ..renderer.yaml import YamlRenderer
from ._decorators import element
from ._grammar import _GrammarMixin
from ._grammar_export import _class_schema_to_grammar_document
from ._utilities import (
    _extract_validators_from_signature,
    _iter_data_element_methods,
    _pop_decorated_methods,
)
from .source_bag import SourceBag


class BuilderBase(
    _GrammarMixin,
    ABC,
):
    """Abstract base class for Bag builders (grammar only).

    A builder declares the dialect via decorators:
        - @element: Pure schema elements (body MUST be empty)
        - @abstract: Define sub_tags for inheritance (cannot be instantiated)

    Sub-builders and the three data-elements (data_setter / data_formula /
    data_controller) are NOT separate decorators: they are ordinary
    @element marked in their ``_meta`` — ``_meta['subbuilder']`` for a
    dialect boundary, ``_meta['data_element']`` for a data-element. They go
    through the same schema and the same ``_command_on_node`` dispatch as
    any element; the element's ``_meta`` rides onto the node and readers
    query it via ``node._get_meta(...)``. The data-elements are declared on
    this base and injected into every dialect's schema by
    ``__init_subclass__`` (see ``_iter_data_element_methods``).

    Engine concerns (source, lifecycle phases, render_target,
    node_id) belong to the BuilderHandler.
    """

    _class_schema: Bag  # Schema built from decorators at class definition

    # -----------------------------------------------------------------------
    # Builder registry (class-level, shared across all dialects)
    # -----------------------------------------------------------------------

    #: Canonical name of this dialect (e.g. ``"html"``, ``"svg"``).
    #: Concrete dialects MUST declare ``_name`` as a class attribute to
    #: appear in :attr:`register`. Builders that leave ``_name = None``
    #: (the default) are not registered — useful for abstract bases
    #: or internal-only classes.
    _name: str | None = None

    #: Class-level dict mapping ``_name`` to the Builder class. Populated
    #: automatically in :meth:`__init_subclass__` whenever a subclass
    #: declares ``_name``. Lookup via :meth:`get_builder_class`. Named
    #: ``_registry`` (not ``register``) to avoid shadowing the
    #: ``ABCMeta.register`` virtual-subclass method inherited via ABC.
    _registry: ClassVar[dict[str, type]] = {}

    #: Case-insensitive tag map (lowercase key -> canonical label), rebuilt
    #: per subclass in :meth:`__init_subclass__`. Declared here so the type
    #: is known at class scope (it cannot be annotated on the ``cls`` target).
    #: Not a ClassVar: ``__init__`` binds it onto each instance as well.
    _schema_tag_names: dict[str, str]

    #: @struct_method dispatch map (lowercase dispatch name -> attr name),
    #: rebuilt per subclass in :meth:`__init_subclass__`. A struct-method is
    #: a callable block invocable from any node (``node.card(...)``); the
    #: dispatcher resolves it through the active builder (legacy
    #: gnrwebstruct parity).
    _struct_methods: dict[str, str]

    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Build _class_schema Bag from decorated methods (@element,
        @abstract). Sub-builders are @element (marked ``_meta['subbuilder']``)
        and collected like any element; the data-elements are injected from
        the base afterwards (see below)."""
        super().__init_subclass__(**kwargs)

        parent_schema = None
        for base in cls.__mro__[1:]:
            if hasattr(base, "_class_schema"):
                parent_schema = base._class_schema
                break
        cls._class_schema = Bag(source=parent_schema) if parent_schema else Bag()

        # Ensure the dedicated sub-bag for abstracts exists. Abstracts
        # live in a nested Bag rather than at the top level, with no `@`
        # prefix on labels. This keeps element / subbuilder / data_element
        # names cleanly separated from the abstract namespace.
        if cls._class_schema.get_node("_abstracts") is None:
            cls._class_schema.set_item("_abstracts", Bag())

        for tag_list, method_name, obj, decorator_info in _pop_decorated_methods(cls, BuilderBase):
            if method_name:
                setattr(cls, method_name, obj)

            is_abstract = decorator_info.get("abstract", False)
            sub_tags = decorator_info.get("sub_tags", "")
            parent_tags = decorator_info.get("parent_tags")
            inherits_from = decorator_info.get("inherits_from", "")
            meta = decorator_info.get("_meta")
            documentation = obj.__doc__
            call_args_validations = _extract_validators_from_signature(obj)

            for tag in tag_list:
                if is_abstract:
                    cls._class_schema["_abstracts"].set_item(
                        tag, None,
                        sub_tags=sub_tags,
                        parent_tags=parent_tags,
                        inherits_from=inherits_from,
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

        # Inject the data-element stubs declared on BuilderBase into this
        # subclass schema. They are @element marked with _meta['data_element'];
        # _pop_decorated_methods skips the base, so they reach every dialect
        # only here. Injected AFTER the dialect's own elements so a data-element
        # (e.g. ``data``) overrides a same-named dialect tag (e.g. HTML <data>).
        for tag_list, obj, decorator_info in _iter_data_element_methods(BuilderBase):
            call_args_validations = _extract_validators_from_signature(obj)
            for tag in tag_list:
                cls._class_schema.set_item(
                    tag, None,
                    sub_tags=decorator_info.get("sub_tags", ""),
                    parent_tags=decorator_info.get("parent_tags"),
                    inherits_from=decorator_info.get("inherits_from", ""),
                    _meta=decorator_info.get("_meta"),
                    documentation=obj.__doc__,
                    call_args_validations=call_args_validations,
                )

        # Validate `inherits_from` references: each name in the
        # comma-separated list must exist among the abstracts. Errors
        # are raised at class definition time so dialect authors see
        # them immediately (no silent fallback at instantiation).
        abstracts_bag = cls._class_schema["_abstracts"]
        known_abstracts = {node.label for node in abstracts_bag}
        for node in cls._class_schema:
            if node.label == "_abstracts":
                continue
            raw = node.get_attr("inherits_from")
            if not raw:
                continue
            for parent in (p.strip() for p in raw.split(",")):
                if not parent:
                    continue
                if parent not in known_abstracts:
                    raise ValueError(
                        f"{cls.__name__}.{node.label}: "
                        f"inherits_from={parent!r} not found among abstracts; "
                        f"available: {sorted(known_abstracts)}"
                    )

        cls._schema_tag_names = {}
        for node in cls._class_schema.nodes:
            label = node.label
            if label.startswith("_"):
                continue
            key = label.lower()
            if key in cls._schema_tag_names:
                existing = cls._schema_tag_names[key]
                raise ValueError(
                    f"Duplicate (case-insensitive) tag in {cls.__name__}: "
                    f"{existing!r} and {label!r} both lowercase to {key!r}"
                )
            cls._schema_tag_names[key] = label

        # @struct_method dispatch map (legacy gnrwebstruct parity): dispatch
        # name = explicit ``@struct_method('alias')`` if given, else attr name
        # with the prefix-before-first-underscore stripped, else attr name;
        # stored lowercase; reverse-MRO merge for inheritance; same dispatch
        # name on a different attr name collides. Struct methods are skipped
        # by _pop_decorated_methods, so they stay callable on the class.
        merged: dict[str, str] = {}
        for klass in reversed(cls.__mro__):
            parent_map = klass.__dict__.get("_struct_methods")
            if parent_map:
                merged.update(parent_map)
        for attr_name, obj in cls.__dict__.items():
            decorator = getattr(obj, "_decorator", None)
            if decorator is None or not decorator.get("struct_method"):
                continue
            explicit = decorator.get("name")
            if explicit is not None:
                dispatch_name = explicit
            elif "_" in attr_name:
                dispatch_name = attr_name.split("_", 1)[1]
            else:
                dispatch_name = attr_name
            key = dispatch_name.lower()
            existing = merged.get(key)
            if existing is not None and existing != attr_name:
                raise ValueError(
                    f"@struct_method '{dispatch_name}' is already tied to "
                    f"implementation method '{existing}' (cannot rebind to "
                    f"'{attr_name}')"
                )
            merged[key] = attr_name
        cls._struct_methods = merged

        name = cls.__dict__.get("_name")
        if name is not None:
            if not isinstance(name, str):
                raise TypeError(
                    f"{cls.__name__}._name must be str, got {type(name).__name__}"
                )
            existing_builder = BuilderBase._registry.get(name)
            if existing_builder is not None and existing_builder is not cls:
                raise ValueError(
                    f"Builder name {name!r} already registered to "
                    f"{existing_builder.__name__}; cannot register {cls.__name__}"
                )
            BuilderBase._registry[name] = cls

    @classmethod
    def get_builder_class(cls, name: str) -> type:
        """Look up a registered Builder class by its canonical ``_name``.

        If ``name`` is not in the registry, attempts a lazy import of
        ``genro_builders.contrib.<name>`` to give the dialect a chance
        to register itself via ``__init_subclass__``. This keeps the
        ``_meta['subbuilder']`` references decoupled from import
        order: mutual references (HTML <-> SVG) need not eagerly
        import each other.

        Raises:
            LookupError: if no builder is registered under ``name``
                after the auto-import attempt.
        """
        if name not in BuilderBase._registry:
            with contextlib.suppress(ImportError):
                __import__(f"genro_builders.contrib.{name}")
        try:
            return BuilderBase._registry[name]
        except KeyError:
            raise LookupError(f"No builder registered with name {name!r}") from None

    @classmethod
    def to_grammar(cls, path: str | Path) -> None:
        """Serialize the grammar to a ``builder_grammar`` v1.0 JSON file.

        The output is a language-neutral document that describes the
        builder's grammar (two sections: abstracts and elements;
        sub-builders and data-elements are elements marked in ``_meta``)
        so that a consumer in another environment can reconstruct an
        equivalent schema.

        Format specification: see ``GRAMMAR_FORMAT.md`` co-located
        with this module.

        Args:
            path: Destination file path. Recommended basename matches
                the grammar name (e.g. ``html.json``).
        """
        document = _class_schema_to_grammar_document(cls)
        Path(path).write_text(
            json.dumps(document, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def __init__(self) -> None:
        """Initialize the builder: grammar state plus the source wrapper.

        Renderers are exposed as ``renderer_<mode>`` properties on the
        builder class. The base class declares ``renderer_xml`` so the
        ``xml`` mode is always available; concrete dialects declare
        their own (``renderer_html`` on ``HtmlBuilder`` etc.).

        The source lives under a stable ``main`` segment of a wrapper
        root, exactly as the handler arranges it: ``self.source`` is the
        payload the ``main`` recipe populates, ``_sourceroot`` the wrapper
        that carries it. ``handler=None`` — a bare builder renders itself
        with no data and no reactivity.
        """
        self._schema = type(self)._class_schema
        self._schema_tag_names = type(self)._schema_tag_names
        self._sourceroot: SourceBag = SourceBag(builder=self, handler=None)
        self._sourceroot["main"] = SourceBag(builder=self, handler=None)
        self.source: SourceBag = self._sourceroot["main"]
        self._sourceroot.set_backref()
        self._default_targets: dict[str, Any] = {}

    @property
    def renderer_xml(self) -> XmlRenderer:
        """Fresh ``XmlRenderer`` instance bound to this builder.

        Each access returns a new instance: the renderer is meant to be
        ephemeral, used for a single ``render`` call and discarded.
        Inherited by every concrete dialect so ``xml`` is always
        available as a render mode.
        """
        return XmlRenderer(builder=self)

    @property
    def renderer_yaml(self) -> YamlRenderer:
        """Fresh ``YamlRenderer`` instance bound to this builder.

        Inherited by every dialect so ``yaml`` is always available as a
        render mode. PyYAML is an optional dependency (extra ``[yaml]``):
        the renderer raises a clear error at render time if it is absent.
        """
        return YamlRenderer(builder=self)

    def new_root(self) -> SourceBag:
        """Return a fresh, throw-away ``SourceBag`` driven by this builder.

        The returned source carries this builder (so the grammar API
        works: ``root.div(...)`` etc.) and has backref enabled (so
        ``parent_node`` is usable). It carries **no handler**: it is not
        connected to a pointer_map, has no reactive subscribes, cannot
        ``create()`` or ``render()``.

        Typical use: pre-build a subtree offline, then attach it as the
        value of some node in a live source — the resulting ``ins`` event
        re-renders, and the render registers the new subtree's pointers at
        read time. The throw-away root itself is not retained by anything.
        """
        root = SourceBag(builder=self, handler=None)
        root.set_backref()
        return root

    def get_subbuilder(self, name: str) -> Any:
        """Return a sub-builder instance by canonical name.

        Looks up the class in the global registry via
        :meth:`get_builder_class` and instantiates it. Used when a
        ``_meta['subbuilder']`` element switches the active dialect
        mid-document (e.g. ``body.svg(...)`` inside HTML).
        """
        return type(self).get_builder_class(name)()

    def main(self, root: SourceBag) -> None:
        """Build the document into ``root``. Override on a page subclass.

        The base raises: a bare builder is grammar, not a renderable page.
        """
        raise NotImplementedError(
            f"{type(self).__name__} has no 'main': it is grammar, not a "
            "renderable page",
        )

    def create(self) -> None:
        """Build the document by running ``main`` on the source.

        The source wrapper is set up in ``__init__``; ``create`` only runs
        the recipe. Kept separate from ``render`` so the build phase stays
        distinct (and so data can seed it in later phases).
        """
        self.main(self.source)

    def render(self, mode: str | None = None, target: Any = None, **opts: Any) -> Any:
        """Render the built source via ``renderer_<mode>``.

        Pointer-free path: the builder renders itself, no handler needed.
        ``mode`` defaults to the dialect's ``_default_render_mode``;
        ``target`` follows :meth:`_get_target` (``False`` returns the
        string, a falsy value falls back to a registered target, a truthy
        value is used directly).
        """
        mode = mode or self._default_render_mode
        renderer = getattr(type(self), f"renderer_{mode}").__get__(self, type(self))
        result = renderer.render_children(renderer.preprocess(self.source), **opts)
        return renderer.finalize(result, self._get_target(target, renderer), **opts)

    def _get_target(self, target: Any, renderer: Any) -> Any:
        """Resolve the render target for a render call.

        - ``False`` → return-as-value: ``None`` for a string renderer, an
          error for an object renderer (no string to return);
        - any other falsy value → the target registered for the renderer's
          mode via :meth:`set_render_target` (``None`` if none);
        - a truthy value → used as-is.
        """
        if target is False:
            if renderer.render_type != "string":
                raise TypeError(
                    f"target=False (return-as-value) is not valid for an "
                    f"object renderer ({type(renderer).__name__})",
                )
            return None
        return target or self._default_targets.get(renderer.mode)

    def set_render_target(self, mode: str, target: Any) -> None:
        """Register a render target for ``mode``.

        Overrides any previous registration under the same mode. A target
        passed explicitly to :meth:`render` still wins over the registered
        one. The dialect's ``_default_render_mode`` is the rendering mode
        and is not changed here.
        """
        self._default_targets[mode] = target

    def include_components(self, *mixins: type) -> None:
        """Enrich THIS instance's grammar with the @component methods
        of the given mixin classes.

        Per-instance: the class schema (and its tag-name map) is copied
        on first use, so other instances of the same builder are left
        untouched. Each component method is bound onto the instance
        (it is already callable — components are never delattr'd) and
        registered in the schema marked ``_meta['component']``, so the
        node API (``node.<name>(...)``) finds it. A component overrides
        a same-named plain element (last-wins, like data-elements).

        Called by ``BuilderHandler.pyrequires`` before ``create()``.
        """
        if self._schema is type(self)._class_schema:
            self._schema = Bag(source=self._schema)
            self._schema_tag_names = dict(self._schema_tag_names)
        for mixin in mixins:
            for name, obj in vars(mixin).items():
                decorator = getattr(obj, "_decorator", None)
                if not decorator:
                    continue
                if not (decorator.get("_meta") or {}).get("component"):
                    continue
                setattr(self, name, obj.__get__(self))
                self._schema.set_item(
                    name, None,
                    sub_tags=decorator.get("sub_tags", ""),
                    parent_tags=decorator.get("parent_tags"),
                    inherits_from=decorator.get("inherits_from", ""),
                    _meta=decorator.get("_meta"),
                    documentation=obj.__doc__,
                    call_args_validations=_extract_validators_from_signature(obj),
                )
                self._schema_tag_names[name.lower()] = name

    # -----------------------------------------------------------------------
    # Data-elements (core, every dialect inherits them). Plain @element marked
    # ``_meta['data_element']``: bodies ignored (like every @element), injected
    # into each dialect schema by __init_subclass__ via
    # _iter_data_element_methods, and dispatched through the same
    # _command_on_node as any element (element_call flags _is_data_element).
    # The signature carries the kind's fields (destination/value/func). The
    # func-bearing kinds (formula/controller) also declare ``_on_start``: a
    # control flag (compute at first calculation), excluded from the func
    # bindings because it is part of the element signature, not a kwarg.
    # -----------------------------------------------------------------------

    @element(_meta={"data_element": True})
    def data_setter(self, destination: str, value: Any): ...

    @element(_meta={"data_element": True})
    def data_formula(
        self, destination: str, func: str | Callable,
        _on_start: bool = False, **kwargs,
    ): ...

    @element(_meta={"data_element": True})
    def data_controller(
        self, func: str | Callable, _on_start: bool = False, **kwargs,
    ): ...

    #: Default rendering mode used when ``render(mode=None)`` is called.
    #: Concrete dialects override this (e.g. ``"html"`` for HtmlBuilder).
    _default_render_mode: str = "xml"

    #: Structural meta-attributes carried by nodes of this grammar:
    #: identity, anchors and the datapath root — not domain attributes.
    #: ``runtime_values`` drops them from the actualized attribute view,
    #: so they never reach a renderer or a data-element binding; their
    #: readers (``node_by_id``, ``abs_datapath``) take them straight from
    #: ``node.attr``. ``datapath`` is binding state (the relative-pointer
    #: root), not markup: it is read by ``abs_datapath`` along the
    #: ancestor chain, never emitted. A dialect that introduces a new
    #: node-meta extends this set, e.g.
    #: ``_meta_attrs = BuilderBase._meta_attrs | {"_my_marker"}``.
    _meta_attrs: frozenset[str] = frozenset(
        {"node_id", "_meta", "_anchor", "datapath"},
    )
