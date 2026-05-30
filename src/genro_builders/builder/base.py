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

import contextlib
import json
from abc import ABC
from pathlib import Path
from typing import Any, ClassVar

from genro_bag import Bag

from ..renderer import XmlRenderer
from ..source_bag import BuilderSource
from ._grammar import _GrammarMixin
from ._grammar_export import _class_schema_to_grammar_document
from ._utilities import _extract_validators_from_signature, _pop_decorated_methods


class BagBuilderBase(
    _GrammarMixin,
    ABC,
):
    """Abstract base class for Bag builders (grammar only).

    A builder declares the dialect via decorators:
        - @element: Pure schema elements (body MUST be empty)
        - @abstract: Define sub_tags for inheritance (cannot be instantiated)
        - @data_element: Data-infrastructure elements.

    Plus @subbuilder, which is **autonomous**: it does not pass through
    ``__init_subclass__`` and does not appear in ``_class_schema``. Its
    wrapper lives on the builder class as a regular method; dispatch is
    handled by ``_BuilderBagNodeMixin.__getattr__`` falling through to
    ``_attach_subbuilder``.

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

    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Build _class_schema Bag from decorated methods (@element,
        @abstract, @data_element). @subbuilder is autonomous and is
        not collected here."""
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

        for tag_list, method_name, obj, decorator_info in _pop_decorated_methods(cls, BagBuilderBase):
            if method_name:
                setattr(cls, method_name, obj)

            is_abstract = decorator_info.get("abstract", False)
            is_data_element = decorator_info.get("data_element", False)
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
                elif is_data_element:
                    cls._class_schema.set_item(
                        tag, None,
                        handler_name=method_name,
                        is_data_element=True,
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

        name = cls.__dict__.get("_name")
        if name is not None:
            if not isinstance(name, str):
                raise TypeError(
                    f"{cls.__name__}._name must be str, got {type(name).__name__}"
                )
            existing_builder = BagBuilderBase._registry.get(name)
            if existing_builder is not None and existing_builder is not cls:
                raise ValueError(
                    f"Builder name {name!r} already registered to "
                    f"{existing_builder.__name__}; cannot register {cls.__name__}"
                )
            BagBuilderBase._registry[name] = cls

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
        if name not in BagBuilderBase._registry:
            with contextlib.suppress(ImportError):
                __import__(f"genro_builders.contrib.{name}")
        try:
            return BagBuilderBase._registry[name]
        except KeyError:
            raise LookupError(f"No builder registered with name {name!r}") from None

    @classmethod
    def to_grammar(cls, path: str | Path) -> None:
        """Serialize the grammar to a ``builder_grammar`` v1.0 JSON file.

        The output is a language-neutral document that describes the
        builder's grammar (abstracts, subbuilders, elements,
        data_elements) so that a consumer in another environment can
        reconstruct an equivalent schema.

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
        """Initialize the builder. Grammar-only state (decisions 1, 8 v0.4.0).

        Renderers are exposed as ``renderer_<mode>`` properties on the
        builder class. The base class declares ``renderer_xml`` so the
        ``xml`` mode is always available; concrete dialects declare
        their own (``renderer_html`` on ``HtmlBuilder`` etc.).
        """
        self._schema = type(self)._class_schema
        self._schema_tag_names = type(self)._schema_tag_names

    @property
    def renderer_xml(self) -> XmlRenderer:
        """Fresh ``XmlRenderer`` instance bound to this builder.

        Each access returns a new instance: the renderer is meant to be
        ephemeral, used for a single ``render`` call and discarded.
        Inherited by every concrete dialect so ``xml`` is always
        available as a render mode.
        """
        return XmlRenderer(builder=self)

    def new_root(self) -> BuilderSource:
        """Return a fresh, throw-away ``BuilderSource`` driven by this builder.

        The returned source carries this builder (so the grammar API
        works: ``root.div(...)`` etc.) and has backref enabled (so
        ``parent_node`` is usable). It carries **no handler**: it is not
        connected to a pointer_map, has no reactive subscribes, cannot
        ``create()`` or ``render()``.

        Typical use: pre-build a subtree offline, then attach it as the
        value of some node in a live source — the resulting ``ins`` event
        on the live source triggers ``register_pointer`` for the new
        subtree. The throw-away root itself is not retained by anything.
        """
        root = BuilderSource(builder=self, handler=None)
        root.set_backref()
        return root

    #: Default rendering mode used when ``render(mode=None)`` is called.
    #: Concrete dialects override this (e.g. ``"html"`` for HtmlBuilder).
    _default_render_mode: str = "xml"
