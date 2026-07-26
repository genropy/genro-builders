# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderBase — grammar base class for Bag builders.

A builder declares the grammar of a dialect via decorators
(@element, @abstract) and the schema of valid tag placements
(sub_tags, parent_tags). Sub-builders and data-elements are ordinary
@element marked in their ``_meta`` (no dedicated decorator). The three data-elements
(dataSetter / dataFormula / dataController) are ordinary @element
declared on this base and marked ``_meta['data_element']``. A builder
renders itself: it owns its source (under the ``main`` segment of a
wrapper root), the create/render phases, the first calculation and the
per-builder node_id lookup. The data store is supplied by the
BuilderHandler; reactivity (live render) is a later phase.

Exports:
    BuilderBase: Base class for all builders.
"""

from __future__ import annotations

import contextlib
import inspect
import json
import re
from abc import ABC
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, ClassVar

from genro_bag import Bag

from ..renderer.xml import XmlRenderer
from ..renderer.yaml import YamlRenderer
from ._decorators import element
from ._grammar import _GrammarMixin
from ._grammar_export import _class_schema_to_grammar_document
from ._utilities import (
    _extract_signature_info,
    _iter_data_element_methods,
    _parse_sub_tags_spec,
    _pop_decorated_methods,
)
from .source_bag import SourceBag
from .target_wrapper import TargetWrapper

# Template token spotted by ``runtime_values`` for ``${name}`` placeholders.
_TEMPLATE_RE = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

#: Structural key of the source wrapper. It exists only so the source is
#: a tree, not a forest; it is NOT an address. Queue keys and every
#: cross-builder identity use the builder's mount ``name`` instead, and
#: paths that travel outside the builder are composed relative to
#: ``builder.source`` (this segment never appears in them).
SOURCE_ROOT = "_root_"


class BuilderBase(
    _GrammarMixin,
    ABC,
):
    """Abstract base class for Bag builders (grammar only).

    A builder declares the dialect via decorators:
        - @element: Pure schema elements (body MUST be empty)
        - @abstract: Define sub_tags for inheritance (cannot be instantiated)

    Sub-builders and the three data-elements (dataSetter / dataFormula /
    dataController) are NOT separate decorators: they are ordinary
    @element marked in their ``_meta`` — ``_meta['subbuilder']`` for a
    dialect boundary, ``_meta['data_element']`` for a data-element. They go
    through the same schema and the same ``_command_on_node`` dispatch as
    any element; the element's ``_meta`` rides onto the node and readers
    query it via ``node._get_meta(...)``. The data-elements are declared on
    this base and injected into every dialect's schema by
    ``__init_subclass__`` (see ``_iter_data_element_methods``).

    Source, lifecycle phases, render_target and node_id belong to the
    builder itself; the data store comes from the BuilderHandler.
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

    #: @container dispatch map (lowercase dispatch name -> attr name),
    #: rebuilt per subclass in :meth:`__init_subclass__`. A container is
    #: a callable block invocable from any node (``node.card(...)``); the
    #: dispatcher resolves it through the active builder (legacy
    #: gnrwebstruct parity).
    _containers: dict[str, str]

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

        for tag_list, obj, decorator_info in _pop_decorated_methods(cls, BuilderBase):
            is_abstract = decorator_info.get("abstract", False)
            sub_tags = decorator_info.get("sub_tags", "")
            parent_tags = decorator_info.get("parent_tags")
            inherits_from = decorator_info.get("inherits_from", "")
            meta = decorator_info.get("_meta")
            documentation = obj.__doc__
            call_args_validations, declared_names, accepts_var_keyword = (
                _extract_signature_info(obj))
            node_label = decorator_info.get("node_label")
            collection_key = decorator_info.get("collection_key")
            # ``ns`` (namespace prefix) is optional: only the elements that
            # declare it carry the attribute, so nodes without a namespace
            # stay clean and the inherits_from merge (``not result[k]``) is
            # never tripped by a spurious ``ns=None``.
            ns = decorator_info.get("ns")
            ns_attr = {"ns": ns} if ns is not None else {}

            for tag in tag_list:
                if is_abstract:
                    cls._class_schema["_abstracts"].set_item(
                        tag, None,
                        sub_tags=sub_tags,
                        parent_tags=parent_tags,
                        inherits_from=inherits_from,
                        _meta=meta,
                        documentation=documentation,
                        **ns_attr,
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
                        declared_names=declared_names,
                        accepts_var_keyword=accepts_var_keyword,
                        node_label=node_label,
                        collection_key=collection_key,
                        **ns_attr,
                    )

        # Inject the data-element stubs declared on BuilderBase into this
        # subclass schema. They are @element marked with _meta['data_element'];
        # _pop_decorated_methods skips the base, so they reach every dialect
        # only here. Injected AFTER the dialect's own elements so a data-element
        # (e.g. ``data``) overrides a same-named dialect tag (e.g. HTML <data>).
        for tag_list, obj, decorator_info in _iter_data_element_methods(BuilderBase):
            call_args_validations, declared_names, accepts_var_keyword = (
                _extract_signature_info(obj))
            for tag in tag_list:
                cls._class_schema.set_item(
                    tag, None,
                    sub_tags=decorator_info.get("sub_tags", ""),
                    parent_tags=decorator_info.get("parent_tags"),
                    inherits_from=decorator_info.get("inherits_from", ""),
                    _meta=decorator_info.get("_meta"),
                    documentation=obj.__doc__,
                    call_args_validations=call_args_validations,
                    declared_names=declared_names,
                    accepts_var_keyword=accepts_var_keyword,
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

        # Validate sub_tags specs eagerly: a grammar typo must surface at
        # class definition, not at the first lazy _get_schema_info. The
        # parse is discarded here; the cached compile happens lazily.
        for node in cls._class_schema:
            spec = node.get_attr("sub_tags")
            if spec:
                try:
                    _parse_sub_tags_spec(spec)
                except ValueError as exc:
                    raise ValueError(
                        f"{cls.__name__}.{node.label}: {exc}"
                    ) from None

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

        # @container dispatch map (legacy gnrwebstruct parity): dispatch
        # name = explicit ``@container('alias')`` if given, else attr name
        # with the prefix-before-first-underscore stripped, else attr name;
        # stored lowercase; same dispatch name on a different attr name
        # collides. The scan walks the WHOLE reverse MRO (the class's own
        # dict last, so it wins): containers live in plain mixins too
        # (DemoContainers), which have no __init_subclass__ of their
        # own. Containers are skipped by _pop_decorated_methods, so they
        # stay callable on the class.
        merged: dict[str, str] = {}
        for klass in reversed(cls.__mro__):
            parent_map = klass.__dict__.get("_containers")
            if parent_map:
                merged.update(parent_map)
            for attr_name, obj in klass.__dict__.items():
                decorator = getattr(obj, "_decorator", None)
                if decorator is None or not decorator.get("container"):
                    continue
                explicit = decorator.get("name")
                dispatch_name = explicit if explicit is not None else attr_name
                key = dispatch_name.lower()
                existing = merged.get(key)
                if existing is not None and existing != attr_name:
                    raise ValueError(
                        f"@container '{dispatch_name}' is already tied to "
                        f"implementation method '{existing}' (cannot rebind "
                        f"to '{attr_name}')"
                    )
                merged[key] = attr_name
        cls._containers = merged

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

    def __init__(self, name: str | None = None) -> None:
        """Initialize the builder: identity, grammar state, source wrapper.

        ``name`` is the builder's identity — a label, not an address: the
        datastore is flat, so the name is no longer a path segment.
        Omitted, it defaults to the dialect typology (``_name``, e.g.
        ``"html"``); a builder with no name at all is rejected at
        ``add_builder``.

        Renderers are exposed as ``renderer_<mode>`` properties on the
        builder class. The base class declares ``renderer_xml`` so the
        ``xml`` mode is always available; concrete dialects declare
        their own (``renderer_html`` on ``HtmlBuilder`` etc.).

        The source lives under the structural ``SOURCE_ROOT`` segment of
        a wrapper root (tree-not-forest guarantee, never an address):
        ``self.source`` is the payload the ``main`` recipe populates,
        ``_sourceroot`` the wrapper that carries it. ``handler=None`` —
        a bare builder renders itself with no data and no reactivity.
        """
        self.name: str | None = name or type(self)._name
        self._schema = type(self)._class_schema
        self._schema_tag_names = type(self)._schema_tag_names
        self._sourceroot: SourceBag = SourceBag(builder=self, handler=None)
        self._sourceroot[SOURCE_ROOT] = SourceBag(builder=self, handler=None)
        self.source: SourceBag = self._sourceroot[SOURCE_ROOT]
        self._sourceroot.set_backref()
        self._default_targets: dict[str, Any] = {}
        # Data source. ``handler`` is set when a BuilderHandler mounts this
        # builder (add_builder); ``data`` is then the handler's store,
        # whole. A bare builder (no_data) keeps handler=None and an empty
        # data bag, so setup(self.data) is harmless.
        self.handler: Any = None
        self.data: Bag = Bag()
        # data-element logic sources, resolved lazily by ``data_logic``.
        self._data_logic: list[Any] | None = None
        # Sub-builder instances, one per dialect name (see get_subbuilder).
        self._subbuilders: dict[str, Any] = {}
        # Per-document DOM-id serial (see ``target_id``): the root builder
        # is the identity authority, sub-builder subtrees draw from the
        # host's counter through ``node.root_builder``.
        self._target_serial: int = 0

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

    def _expansion_root(self, datapath: str | None = None) -> SourceBag:
        """Fresh throw-away root for a component expansion (CMP.2).

        Same structural shape as the document source — a payload under
        ``SOURCE_ROOT`` inside a wrapper: the wrapper is the transparent
        throw-away container the design names (discarded with the whole
        expansion, never an address), and the expansion nodes get real
        fullpaths (pretty depth, future path arithmetic). Unlike
        :meth:`new_root`, the result is not meant to be attached
        anywhere: it is built, rendered and dropped.

        ``datapath`` is the expansion's data anchor (the component's
        ``store``, CMP.3): stamped on the structural node — the wrapper
        is the machinery's own object — so the body's relative pointers
        (``^.company``) find it through the ordinary ancestor climb.
        """
        wrapper = SourceBag(builder=self, handler=None)
        attrs = {"datapath": datapath} if datapath else {}
        wrapper.set_item(
            SOURCE_ROOT, SourceBag(builder=self, handler=None),
            _attributes=attrs,
        )
        wrapper.set_backref()
        return wrapper[SOURCE_ROOT]

    def get_subbuilder(self, name: str) -> Any:
        """Return THE sub-builder instance for ``name``, cached per host.

        Looks up the class in the global registry via
        :meth:`get_builder_class`, instantiates it once and memoises it
        (the same pattern as the renderer cache: one instance per host
        per dialect, so every ``<svg>`` subtree of the document shares
        one ``SvgBuilder`` and the renderer cache keyed by
        ``id(builder)`` serves them all with a single sub-renderer).
        Used when a ``_meta['subbuilder']`` element switches the active
        dialect mid-document (e.g. ``body.svg(...)`` inside HTML). The
        host's handler is passed on so the sub-builder resolves pointers
        against the same document data; it cascades to nested
        sub-builders, and is re-synced on every hit so a host mounted
        after a first bare render keeps the invariant.
        """
        subbuilder = self._subbuilders.get(name)
        if subbuilder is None:
            subbuilder = type(self).get_builder_class(name)()
            self._subbuilders[name] = subbuilder
        subbuilder.handler = self.handler
        return subbuilder

    def main(self, root: SourceBag) -> None:
        """Build the document into ``root``. Override on a page subclass.

        The base raises: a bare builder is grammar, not a renderable page.
        """
        raise NotImplementedError(
            f"{type(self).__name__} has no 'main': it is grammar, not a "
            "renderable page",
        )

    def setup(self, data: Any) -> None:
        """Override point: populate this builder's data segment.

        Receives the builder's own data bag (its segment when mounted,
        an empty bag otherwise). Default no-op — a page with pointers
        overrides it to seed the values its ``main`` reads. Called by
        :meth:`create` before ``main``.
        """

    def create(self) -> None:
        """Build the document, then run the first calculation.

        Sequence: ``setup(self.data)`` seeds the data, ``main(self.source)``
        builds the document, then the first calculation runs every
        ``dataSetter`` (it seeds the data) plus any ``dataFormula`` /
        ``dataController`` flagged ``_on_start``. Reactivity (source/data
        subscribes) is armed later and is out of scope here.
        """
        self.setup(self.data)
        self.main(self.source)
        self.compute_logic(
            self.source.query(
                what="#n", deep=True,
                condition=lambda n: bool(
                    n._get_meta("data_element")
                    and (n.node_tag == "dataSetter" or n.attr.get("_on_start"))
                ),
            )
        )
        # Reactivity of the SOURCE (structure) lives on the builder. Armed
        # only when reactive: the live phase (subscribe + queue +
        # end-of-live render) is paid by reactive pages, not one-shot ones.
        if self._is_reactive:
            self._sourceroot.subscribe(
                "builder_source",
                insert=self._on_source_event,
                update=self._on_source_event,
                delete=self._on_source_event,
            )

    @property
    def _is_reactive(self) -> bool:
        """True when mounted on a handler that has an application.

        A builder with no data has no handler: it renders one-shot and is
        not reactive. Only a builder on a handler with an application arms
        source reactivity (subscribe + live render).
        """
        return bool(self.handler and self.handler.application)

    def node_by_id(self, node_id: str) -> Any:
        """Return the source node carrying ``node_id`` in this builder.

        Walk-based lookup over this builder's source tree (the node_id
        namespace is per-builder). Raises ``KeyError`` if no node carries
        the requested id.
        """
        node = self.source.get_node_by_attr("node_id", node_id)
        if node is None:
            raise KeyError(node_id)
        return node

    def node_by_target_id(self, target_id: str) -> Any:
        """Return the source node whose serial is ``target_id``.

        The upstream half of the identity bridge: patches go DOWN
        addressed by serial, mutations come UP addressed the same way.
        Walk-based like ``node_by_id`` (the serial lives in a slot, the
        tree is the registry). Raises ``KeyError`` when no node carries
        the serial — expansion content is NOT here: its derived ids
        resolve in ``_writeback_map``.
        """
        queue = [self.source]
        while queue:
            for node in queue.pop(0).nodes:
                if getattr(node, "_target_id", None) == target_id:
                    return node
                if isinstance(node.value, SourceBag):
                    queue.append(node.value)
        raise KeyError(target_id)

    def target_id(self, node: Any) -> str | None:
        """Per-document serial bridging a source node to its DOM element.

        The reactive render emits it as the element's ``id``; patches
        address the DOM through it. Assigned on first emission from the
        root builder's counter (``n1``, ``n2``, ... — render order, so
        deterministic for a given program), stored on the node, never
        recomputed: it is bound to the OBJECT, not to its position, so
        no structural mutation can stale it.

        Expansion nodes (``handler is None``, the D9 gate) get none:
        they reincarnate at every render — no stable identity to bridge.
        Their replacement unit is the enclosing element.
        """
        existing = getattr(node, "_target_id", None)
        if existing is not None:
            return existing
        if node.handler is None:
            return None
        root = node.root_builder
        root._target_serial += 1
        node._target_id = f"n{root._target_serial}"
        return node._target_id

    # ------------------------------------------------------------------
    # Source reactivity (change handling on the builder; pointer-map
    # maintenance delegated to the handler)
    # ------------------------------------------------------------------

    def _on_source_event(
        self, node: Any, evt: str, pathlist: list[str], **kw: Any
    ) -> None:
        """Internal dispatcher for events on this builder's ``_sourceroot``.

        Maintains the handler's ``pointer_map`` coherent across the
        mutation (mapkeep is delegated to the handler — the map is its
        property), then forwards a normalized event to the user hook
        :meth:`on_source_change`. Mapkeep is structural, not user-facing:
        it MUST happen even if the user does not override the public hook.
        """
        if evt == "ins":
            self.on_source_change(node, "ins", evt_detail=None, **kw)
        elif evt == "del":
            self.handler._unregister_pointer(node)
            self.on_source_change(node, "del", evt_detail=None, **kw)
        else:
            detail = evt[4:] if evt.startswith("upd_") else evt
            if detail in ("value", "value_attr"):
                self._on_upd_value(node, kw.get("oldvalue"))
            if detail in ("attrs", "value_attr"):
                self._on_upd_attrs(node, kw.get("attrs_diff") or {})
            self.on_source_change(node, "upd", evt_detail=detail, **kw)

    def on_source_change(
        self, node: Any, evt: str, evt_detail: str | None = None, **kw: Any
    ) -> None:
        """Override point: a node in the source tree changed.

        Normalized event: ``evt`` is ``"ins"`` / ``"del"`` / ``"upd"``,
        ``evt_detail`` carries the update kind for ``"upd"``. Default
        no-op. Runs AFTER the structural pointer-map maintenance.
        """

    def _value_nature(self, v: Any) -> str:
        """Classify a value as ``"bag"``, ``"pointer"`` or ``"scalar"``.

        Used by :meth:`_on_upd_value` to dispatch over the 9-cases matrix
        of value transitions (old kind × new kind).
        """
        if isinstance(v, Bag):
            return "bag"
        if isinstance(v, str) and v.startswith("^"):
            return "pointer"
        return "scalar"

    def _on_upd_value(self, node: Any, oldvalue: Any) -> None:
        """De-register the old value's pointers across an ``upd_value`` event.

        Dispatches over the 9 transitions of (old kind, new kind) where
        each kind is one of ``"scalar"``, ``"pointer"``, ``"bag"`` — see
        :meth:`_value_nature`. Only the OLD side acts: registration of the
        new value is the render's job (read-time ``_register_path``). The
        empty branches are kept explicit as anchor points for the future
        partial-render refactor.
        """
        new = node.value
        old_kind = self._value_nature(oldvalue)
        new_kind = self._value_nature(new)
        match (old_kind, new_kind):
            case ("scalar", "scalar"):
                pass
            case ("scalar", "pointer"):
                pass
            case ("scalar", "bag"):
                pass
            case ("pointer", "scalar"):
                self.handler._update_pointer_map(node, [("", oldvalue)])
            case ("pointer", "pointer"):
                self.handler._update_pointer_map(node, [("", oldvalue)])
            case ("pointer", "bag"):
                self.handler._update_pointer_map(node, [("", oldvalue)])
            case ("bag", "scalar"):
                for old_child in oldvalue:
                    self.handler._unregister_pointer(old_child)
            case ("bag", "pointer"):
                for old_child in oldvalue:
                    self.handler._unregister_pointer(old_child)
            case ("bag", "bag"):
                for old_child in oldvalue:
                    self.handler._unregister_pointer(old_child)

    def _on_upd_attrs(self, node: Any, attrs_diff: dict) -> None:
        """De-register old attr-pointers across an ``upd_attrs`` event.

        ``attrs_diff`` is the per-attribute diff produced by ``genro_bag``:
        ``{attr_name: {"old": old_value, "new": new_value}, ...}``. Only
        the old pointer is de-registered; the new one is re-registered by
        the render that follows.
        """
        for attrname, change in attrs_diff.items():
            old_v = change.get("old")
            if isinstance(old_v, str) and old_v.startswith("^"):
                self.handler._update_pointer_map(node, [(attrname, old_v)])

    # ------------------------------------------------------------------
    # Data-element logic (first calculation; reactive cascade later)
    # ------------------------------------------------------------------

    def compute_logic(self, nodes: Iterable[Any]) -> None:
        """Execute a list of data-element nodes through ``_compute_node``."""
        for node in nodes:
            self._compute_node(node)

    def _compute_node(self, node: Any) -> None:
        """Execute a single data-element node according to its kind.

        - ``dataSetter`` seeds the data: write its value at destination;
        - ``dataFormula`` is pure: ``func(**bindings)`` -> destination;
        - ``dataController`` has side effects: ``func(node, **bindings)``.
        """
        match node.node_tag:
            case "dataSetter":
                # The setter's schema fields and the framework markers
                # stay on the source node; only user attributes ride
                # onto the datum being seeded.
                attrs = {k: v for k, v in node.attr.items()
                         if k not in ("destination", "value")
                         and k not in self._meta_attrs}
                node.set_relative_data(
                    node.attr["destination"], node.attr["value"],
                    attributes=attrs or None,
                )
            case "dataFormula":
                func = self._resolve_logic_func(node.attr["func"])
                node.set_relative_data(
                    node.attr["destination"], func(**self._bindings(node)),
                )
            case "dataController":
                func = self._resolve_logic_func(node.attr["func"])
                func(node, **self._bindings(node))

    def _bindings(self, node: Any) -> dict[str, Any]:
        """Resolve a data-element node's bindings via ``runtime_values``.

        ``runtime_values`` resolves ``^``/``=`` and ``${}``; here we strip
        the element's own schema fields (``destination`` / ``func`` /
        ``value`` / ``_on_start``), so what remains are the func bindings.
        """
        fields = set(self._get_schema_info(node.node_tag).get(
            "call_args_validations") or {})
        _, resolved = self.runtime_values(node)
        return {k: v for k, v in resolved.items() if k not in fields}

    @property
    def data_logic(self) -> list[Any]:
        """Sources searched (left-to-right) to resolve a data-element func.

        Default is ``[self]`` (the builder owns its logic). Subclasses
        override ``_build_data_logic`` to add more sources.
        """
        if self._data_logic is None:
            built = self._build_data_logic()
            self._data_logic = (
                list(built) if isinstance(built, (list, tuple)) else [built]
            )
        return self._data_logic

    def _build_data_logic(self) -> Any:
        """Override point: return the data_logic source(s). Default ``self``."""
        return self

    def _resolve_logic_func(self, name: str) -> Any:
        """Resolve ``name`` to a ``@staticmethod`` over ``data_logic`` sources.

        Left-to-right, first-wins. A source owning the name but NOT as a
        staticmethod raises TypeError; miss on every source raises
        AttributeError.
        """
        for source in self.data_logic:
            try:
                attr = inspect.getattr_static(source, name)
            except AttributeError:
                continue
            if not isinstance(attr, staticmethod):
                raise TypeError(
                    f"data-element func {name!r} on {type(source).__name__} "
                    "must be a @staticmethod",
                )
            return getattr(source, name)
        sources = ", ".join(type(s).__name__ for s in self.data_logic)
        raise AttributeError(
            f"data-element func {name!r} not found on any data_logic "
            f"source ({sources})",
        )

    def runtime_values(self, node: Any) -> tuple[Any, dict[str, Any]]:
        """Resolve the pointers/templates carried by ``node``.

        Returns ``(runtime_value, runtime_attrs)``. Resolution lives on
        the builder (it reaches the handler via ``self.handler``); ``node``
        is just the subject whose pointers are resolved. ``^``/``=``
        strings are read from ``handler.data`` at the node's absolute path;
        ``^`` readers register in the pointer_map; ``${name}`` templates
        expand against the resolved attrs.

        An attribute referenced by a ``${...}`` template of the same node
        is a template input: once expanded it has been consumed, and it is
        dropped from the returned attrs — no renderer emits it. The name
        is free (``w``, ``foo``); it is the usage, visible in the recipe,
        that marks it. Canonical idiom for "computed datum + authored
        unit": ``div(w="^mywidth", width="${w}px")``. An attribute meant
        to be BOTH emitted and reused goes through a template itself:
        ``t="hello", title="${t}", aria_label="${t} world"``.
        """
        is_data_element = bool(node._get_meta("data_element"))
        resolved: dict[Any, Any] = {}
        carried: dict[str, Any] = {}
        for k, v in node.runtime_to_evaluate().items():
            ptype = node.pointer_type(v)
            if not ptype:
                resolved[k] = v
                continue
            abs_path = node.abs_datapath(v)
            value = self.handler.data.get_item(abs_path)
            # Read-time registration — but only for nodes of the live
            # document. Expansion nodes (their root wrapper carries no
            # handler) read and resolve like anyone else, yet never enter
            # the pointer_map: the subscription stays on the component
            # node, whose declared pointers (store/iterate/params) DID
            # register (CMP.7 — coarse subscription, fine resolution).
            if ptype == "^" and node.handler is not None:
                self.handler._register_path(node, abs_path)
            # The datum knows how to present itself. Presentation only:
            # never for a data-element's bindings (formulas want the raw
            # datum) and never for ``?attr`` reads (raw by definition).
            # - ``mask`` wraps the value (legacy gnrformatter vocabulary,
            #   ``%s`` = the value);
            # - ``_wdg`` (value reads only) is a dict of attributes the
            #   datum carries onto its reader — the exception that
            #   travels with the data (e.g. an alarm color).
            if not is_data_element and "?" not in abs_path:
                data_node = self.handler.data.get_node(abs_path)
                if data_node is not None:
                    value = self._present_value(data_node, value)
                    if k is None:
                        wdg = data_node.attr.get("_wdg")
                        if wdg:
                            carried.update(wdg)
            resolved[k] = value

        consumed: set[str] = set()

        def _expand(s: str) -> str:
            def repl(m: re.Match[str]) -> str:
                name = m.group(1)
                consumed.add(name)
                val = resolved[name]
                return "" if val is None else str(val)
            return _TEMPLATE_RE.sub(repl, s)

        for k, v in resolved.items():
            if isinstance(v, str) and "${" in v:
                resolved[k] = _expand(v)

        runtime_value: Any = resolved.pop(None)
        # Template inputs were consumed by the expansion above; they are
        # not part of the node's runtime attrs.
        resolved = {k: v for k, v in resolved.items() if k not in consumed}
        # ``_wdg`` attributes carried by the datum override the recipe's:
        # what travels with the data is the exception, and the exception
        # wins over the static default.
        resolved.update(carried)
        return runtime_value, resolved

    def render(
        self, mode: str | None = None, target: Any = None,
        validate: bool = True, **opts: Any,
    ) -> Any:
        """Render the built source via ``renderer_<mode>``.

        Pointer-free path: the builder renders itself, no handler needed.
        ``mode`` defaults to the dialect's ``_default_render_mode``;
        ``target`` follows :meth:`_get_target` (``False`` returns the
        string, a falsy value falls back to a registered target, a truthy
        value is used directly).

        Pre-render validation: the walk recomputes every node's minimum
        child cardinality; the maximum is enforced at insertion, the
        minimum only makes sense when the document is declared finished —
        which is here, the moment it leaves the system. One error lists
        every incomplete node. ``validate=False`` emits a partial
        document deliberately. For XSD dialects this is the structural
        first net, not a replacement for full XSD validation downstream.
        """
        mode = mode or self._default_render_mode
        renderer = getattr(type(self), f"renderer_{mode}").__get__(self, type(self))
        effective_target = self._get_target(target, renderer)
        if isinstance(effective_target, TargetWrapper):
            # The destination dictates the form of every delivery (e.g. a
            # patch consumer needs the DOM ids): its walk options are the
            # base, the call's own opts win.
            opts = {**effective_target.render_opts, **opts}
        result = renderer.render_children(renderer.preprocess(self.source), **opts)
        if validate and renderer.incomplete:
            problems = "\n".join(
                f"  {path}: missing required children: {', '.join(missing)}"
                for path, missing in renderer.incomplete
            )
            raise ValueError(f"incomplete document:\n{problems}")
        return renderer.finalize(result, effective_target, **opts)

    def _present_value(self, data_node: Any, value: Any) -> Any:
        """Apply the datum's presentation mask.

        The datum knows how to present itself: ``mask`` is a %-format
        whose single argument is the value — ``%s`` wraps (``"%s°"``),
        a numeric directive fixes the shape (``"%.2f"``, ``"€ %.2f"``;
        legacy gnrformatter vocabulary). Bags and missing values pass
        raw; a mask/value mismatch raises — the datum declared a
        presentation it cannot honour.
        """
        mask = data_node.attr.get("mask")
        if mask and value is not None and not isinstance(value, Bag):
            return str(mask) % value
        return value

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

    def set_render_target(self, target: Any, mode: str | None = None) -> None:
        """Register a render target, by default for the dialect's own mode.

        ``mode`` defaults to the dialect's ``_default_render_mode`` (e.g.
        ``"html"`` for HtmlBuilder), so the common case is just
        ``set_render_target("output.html")``. Pass ``mode`` to register a
        target for a different render mode (e.g. an ``xml`` view). A target
        passed explicitly to :meth:`render` still wins over the registered
        one.
        """
        self._default_targets[mode or self._default_render_mode] = target

    @property
    def rendered_target(self) -> str:
        """Read back the file written by the last render to the default mode.

        Returns the text content of the file registered as the target for
        the dialect's ``_default_render_mode`` (a string renderer writes
        its output there). Use after :meth:`render` to inspect what was
        produced without re-rendering.

        Raises:
            KeyError: no target registered for the default mode.
            TypeError: the registered target is not a file path (e.g. a
                writable or a callable) — there is no file to read back.
        """
        mode = self._default_render_mode
        target = self._default_targets.get(mode)
        if target is None:
            raise KeyError(
                f"no render target registered for mode {mode!r}; "
                "call set_render_target first",
            )
        if not isinstance(target, (str, Path)):
            raise TypeError(
                f"render target for mode {mode!r} is not a file path; "
                "there is no file to read back",
            )
        return Path(target).read_text(encoding="utf-8")

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
                    call_args_validations=_extract_signature_info(obj)[0],
                )
                self._schema_tag_names[name.lower()] = name

    # -----------------------------------------------------------------------
    # Data-elements (core, every dialect inherits them). Plain @element marked
    # ``_meta['data_element']``: bodies ignored (like every @element), injected
    # into each dialect schema by __init_subclass__ via
    # _iter_data_element_methods, and dispatched through the same
    # _command_on_node as any element.
    # The signature carries the kind's fields (destination/value/func). The
    # func-bearing kinds (formula/controller) also declare ``_on_start``: a
    # control flag (compute at first calculation), excluded from the func
    # bindings because it is part of the element signature, not a kwarg.
    # -----------------------------------------------------------------------

    @element(_meta={"data_element": True})
    def dataSetter(self, destination: str, value: Any, **attr: Any): ...

    @element(_meta={"data_element": True})
    def dataFormula(
        self, destination: str, func: str | Callable,
        _on_start: bool = False, **kwargs,
    ): ...

    @element(_meta={"data_element": True})
    def dataController(
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
    #: ``ns`` is the namespace prefix: the renderer consumes it to compose
    #: ``<ns>:<tag>`` (in ``_handle_meta``), so it is grammar meta, never
    #: an emitted XML attribute.
    _meta_attrs: frozenset[str] = frozenset(
        {"node_id", "_meta", "_anchor", "datapath", "ns"},
    )

    #: Retained attribute FAMILIES (name prefixes): declared on the
    #: node, readable by whoever resolves the node (the write-back map,
    #: a validation engine), but NEVER emitted by a renderer — they are
    #: server-side contract, not markup. Unlike ``_meta_attrs`` (exact
    #: names, dropped before resolution) a retained family stays in the
    #: actualized view and is filtered at emission. ``validate_`` is
    #: the legacy validation vocabulary; ``dtype`` is the declared data
    #: type a mutation resolves on the node (TYTX) — semantics live in
    #: the application layer, the grammar only guarantees retention.
    _retained_attr_prefixes: tuple[str, ...] = ("validate_", "dtype")
