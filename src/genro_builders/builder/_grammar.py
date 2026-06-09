# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Grammar mixin: element dispatch, validation, schema access.

Interprets the schema defined by decorators to create and validate nodes.
Handles ``__getattr__`` lookup, element and subbuilder creation (the
three data-elements are ordinary elements marked ``_meta['data_element']``,
created through the same path), child placement, all validation checks
(call_args, sub_tags, parent_tags), and schema introspection
(``__contains__``, ``_get_schema_info``, ``__iter__``).
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from genro_bag import Bag

from ._utilities import _check_type, _parse_parent_tags_spec, _parse_sub_tags_spec
from .source_bag import SourceBag

if TYPE_CHECKING:
    from genro_bag import BagNode

    from .source_bag import SourceBagNode


class _GrammarMixin:
    """Mixin for element dispatch, creation, validation, and schema access."""

    # -----------------------------------------------------------------------
    # Bag delegation
    # -----------------------------------------------------------------------

    def _bag_call(self, bag: Bag, name: str) -> Any:
        """Return callable that creates a schema element in the bag.

        Precondition: name is in self._schema.
        """
        handler = self.__getattr__(name)
        return lambda node_value=None, node_label=None, node_position=None, **attr: handler(
            bag,
            _tag=name,
            node_value=node_value,
            node_label=node_label,
            node_position=node_position,
            **attr,
        )

    # -----------------------------------------------------------------------
    # Element dispatch
    # -----------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        """Look up tag in _schema and return handler with validation."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        def wrapper(destination_bag: Bag, *args: Any, node_tag: str = name, **kwargs: Any) -> Any:
            try:
                info = self._get_schema_info(node_tag)
            except KeyError as err:
                raise AttributeError(f"'{type(self).__name__}' has no element '{node_tag}'") from err

            # Validate original kwargs BEFORE the method call
            node_value = args[0] if args else kwargs.get("node_value")
            self._validate_call_args(info, node_value, kwargs)

            # Element: no adapter, register directly with original kwargs
            kwargs.pop("node_value", None)
            kwargs.pop("_tag", None)  # internal marker, never an attribute
            return self._add_element(destination_bag, node_value, node_tag=node_tag, **kwargs)

        return wrapper

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
        return self.set_child(build_where, node_tag, node_value, node_label=node_label, **attr)

    def set_child(
        self,
        build_where: Bag,
        node_tag: str,
        node_value: Any = None,
        node_label: str | None = None,
        node_position: str | int | None = None,
        **attr: Any,
    ) -> BagNode:
        """Create a child node in the target Bag with validation.

        Public entry point for the grammar machine: every ``body.div(...)``,
        ``body.span(...)`` etc. ultimately lands here. Use it directly when
        you need to attach a node whose tag is computed at runtime (rather
        than spelled out as a method name), e.g. when injecting a subtree
        pre-built via ``BuilderBase.new_root``.

        Auto-labels the new node via ``_auto_label`` when ``node_label``
        is omitted, ensuring no collision with existing siblings in
        ``build_where``.

        Raises ValueError if validation fails, KeyError if parent tag not in schema.
        """
        parent_node = build_where.parent_node
        parent_info: dict | None = None
        if parent_node and parent_node.node_tag:
            parent_info = self._get_schema_info(parent_node.node_tag)

        child_info = self._get_schema_info(node_tag)
        self._validate_parent_tags(child_info, parent_node)

        # The element's schema ``_meta`` rides onto the node as a single
        # ``_meta`` attribute (read uniformly via ``node._get_meta``).
        # Done here — the one point both dispatch paths (bag root and
        # node child) converge — so it is never duplicated nor missed on
        # a root node. An explicit ``_meta`` in ``attr`` is left as-is.
        if "_meta" not in attr:
            meta = child_info.get("_meta")
            if meta:
                attr["_meta"] = meta

        node_label = (
            node_label
            or child_info.get("fixed_node_label")
            or self._auto_label(build_where, node_tag)
        )
        child_node = build_where.set_item(
            node_label, node_value, _attributes=dict(attr),
            node_position=node_position, node_tag=node_tag,
        )

        try:
            if parent_info is not None:
                # parent_info is set only inside `if parent_node and ...` above,
                # so a non-None parent_info guarantees a non-None parent_node.
                assert parent_node is not None
                self._validate_sub_tags(parent_node, parent_info)
            self._validate_sub_tags(child_node, child_info)
        except ValueError:
            build_where.pop(node_label)
            raise

        return child_node

    def _auto_label(self, build_where: Bag, node_tag: str) -> str:
        """Generate unique label for a node: tag_0, tag_1, ..."""
        n = 0
        while build_where.node(f"{node_tag}_{n}") is not None:
            n += 1
        return f"{node_tag}_{n}"

    def _command_on_node(
        self,
        node: SourceBagNode,
        child_tag: str,
        node_position: str | int | None = None,
        node_value: Any = None,
        **attrs: Any,
    ) -> Any:
        """Add a child to a node.

        Uses _bag_call for schema elements (handles tag renames).
        Falls back to self.set_child() for unknown tags (provides validation errors).
        """
        if not isinstance(node.value, Bag):
            # Sub-bag must be the same type as the parent bag (e.g. a
            # ``SourceBagNode`` spawns a ``SourceBag`` sub-bag).
            # ``_builder`` is resolved via the node itself
            # (its slot if populated, else ancestors): this lets an
            # @subbuilder node (e.g. <svg>) propagate its own dialect
            # down into the freshly-created sub-bag instead of leaking
            # the host dialect.
            parent_bag = node.parent_bag
            sub_bag_cls = type(parent_bag) if parent_bag is not None else SourceBag
            sub_bag = sub_bag_cls(
                builder=node._resolve_builder(),
                handler=getattr(parent_bag, "_handler", None) if parent_bag else None,
            )
            node.value = sub_bag

        node._check_unique_id(attrs.get("node_id"))

        if child_tag in self._schema:
            callable_handler = self._bag_call(node.value, child_tag)
            return callable_handler(
                node_value=node_value,
                node_position=node_position,
                **attrs,
            )

        # Tag not in schema: use set_child() which will validate and raise
        return self.set_child(
            node.value,
            child_tag,
            node_value=node_value,
            node_position=node_position,
            **attrs,
        )

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

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
            List of tag names whose minimum cardinality was not met
            (required children still missing).

        Raises:
            ValueError: if tag not allowed or max exceeded
        """
        # Wildcard "*" accepts any children - no validation needed.
        # isinstance (not == "*") so mypy narrows the remaining type to dict:
        # _parse_sub_tags_spec returns "*" as its only str value, else a dict.
        if isinstance(sub_tags_compiled, str):
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
        # Subbuilder nodes are transparent containers for the embedded dialect.
        if node._get_meta("subbuilder"):
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
            if self.require_sub_tag_validation(n)
        ] if isinstance(node.value, Bag) else []

        node._invalid_reasons = self._validate_children_tags(
            node.node_tag, sub_tags_compiled, children_tags
        )

    def require_sub_tag_validation(self, node: BagNode) -> bool:
        """Whether ``node`` counts as a child for its parent's sub_tags check.

        Data-elements and subbuilders are structural: invisible to the
        containment grammar. Everything else defers to
        ``custom_require_sub_tag_validation``, the dialect hook.
        """
        meta = node._get_meta("data_element,subbuilder")
        if meta[0] or meta[1]:
            return False
        return self.custom_require_sub_tag_validation(node)

    def custom_require_sub_tag_validation(self, node: BagNode) -> bool:
        """Dialect hook: return False to exempt ``node`` from its parent's
        sub_tags validation. Default validates everything."""
        return True

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

    # -----------------------------------------------------------------------
    # Schema access
    # -----------------------------------------------------------------------

    def __contains__(self, name: str) -> bool:
        """Check if element exists in schema."""
        return self._schema.get_node(name) is not None

    def _get_schema_info(self, name: str) -> dict:
        """Return info dict for a schema element.

        The result is a dict of all schema-node attributes, extended with
        computed keys. Common keys (presence depends on element type):

            sub_tags, sub_tags_compiled, parent_tags, parent_tags_compiled,
            call_args_validations, _meta, documentation.

        Sub-builder and data-element markers are not separate top-level
        keys: they live inside ``_meta`` (``_meta["subbuilder"]`` is the
        dialect name, ``_meta["data_element"]`` flags a data-element).

        Results are cached on the schema node after first access.

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
            abstracts_bag = self._schema["_abstracts"]
            parents = [p.strip() for p in inherits_from.split(",")]
            for parent in parents:
                abstract_attrs = abstracts_bag.get_attr(parent)
                for k, v in abstract_attrs.items():
                    if k == "inherits_from":
                        continue
                    if k == "_meta":
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
        """Iterate over public schema nodes (skips internal labels prefixed by '_')."""
        return (n for n in self._schema if not n.label.startswith("_"))

    def __repr__(self) -> str:
        """Show builder schema summary."""
        count = sum(1 for _ in self)
        return f"<{type(self).__name__} ({count} elements)>"

    def __str__(self) -> str:
        """Show schema structure."""
        return str(self._schema)
