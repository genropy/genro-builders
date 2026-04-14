# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Grammar mixin: element dispatch, component handling, validation, schema access.

Interprets the schema defined by decorators to create and validate nodes.
Handles ``__getattr__`` lookup, element/data_element/component creation,
child placement, all validation checks (call_args, sub_tags, parent_tags),
and schema introspection (``__contains__``, ``_get_schema_info``, ``__iter__``).
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from genro_bag import Bag

from ..builder_bag import BuilderBag
from ._utilities import _check_type, _parse_parent_tags_spec, _parse_sub_tags_spec

if TYPE_CHECKING:
    from genro_bag import BagNode


class _GrammarMixin:
    """Mixin for element dispatch, creation, validation, and schema access."""

    # -----------------------------------------------------------------------
    # Bag delegation
    # -----------------------------------------------------------------------

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

            # Data element: multi-positional args, bypass validation
            if info.get("is_data_element"):
                handler = getattr(self, info["handler_name"])
                path, attrs_dict = handler(*args, **kwargs)
                return self._add_data_element(destination_bag, node_tag, path, attrs_dict)

            # Validate original kwargs BEFORE the method call
            node_value = args[0] if args else kwargs.get("node_value")
            self._validate_call_args(info, node_value, kwargs)

            # Check if this is a component
            if info.get("is_component"):
                return self._handle_component(destination_bag, info, node_tag, kwargs)

            # Element: no adapter, register directly with original kwargs
            kwargs.pop("node_value", None)
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
        return self._child(build_where, node_tag, node_value, node_label=node_label, **attr)

    def _add_data_element(
        self, build_where: Bag, node_tag: str,
        path: str | None, attrs_dict: dict[str, Any],
    ) -> None:
        """Add a data element node to the source bag.

        Not materialized in built. Processed as side effect during build walk.
        Bypasses _child() validation -- data elements are transparent.
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
        if not getattr(build_where, '_skip_parent_validation', False):
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
            self._validation_tag_for(n) for n in node.value.nodes
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
        If child is a component with main_tag, validates using main_tag instead.
        Raises ValueError if not valid.
        """
        sub_tags_compiled = info.get("sub_tags_compiled")
        if sub_tags_compiled is None:
            return

        # Wildcard "*" accepts any children - no validation needed
        if sub_tags_compiled == "*":
            return

        # If child is a component with main_tag, validate as that tag
        validation_tag = child_tag
        child_schema = self._schema.get_node(child_tag)
        if child_schema is not None:
            main_tag = child_schema.attr.get("main_tag")
            if main_tag:
                validation_tag = main_tag

        # Build children_tags = current + new (excluding data elements)
        children_tags = (
            [self._validation_tag_for(n) for n in target_node.value.nodes
             if not n.attr.get("_is_data_element")]
            if isinstance(target_node.value, Bag) else []
        )

        # Insert new tag at correct position
        idx = (
            target_node.value._nodes._parse_position(node_position)
            if isinstance(target_node.value, Bag)
            else 0
        )
        children_tags.insert(idx, validation_tag)

        self._validate_children_tags(target_node.node_tag, sub_tags_compiled, children_tags)

    def _validation_tag_for(self, node: BagNode) -> str:
        """Return the tag to use for validation: main_tag if component, else node_tag."""
        tag = node.node_tag or node.label
        schema_node = self._schema.get_node(tag)
        if schema_node is not None:
            main_tag = schema_node.attr.get("main_tag")
            if main_tag:
                return str(main_tag)
        return tag

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
            call_args_validations, _meta, documentation,
            handler_name, is_component, is_data_element,
            component_builder, based_on, slots.

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
            parents = [p.strip() for p in inherits_from.split(",")]
            for parent in parents:
                abstract_attrs = self._schema.get_attr(parent)
                if abstract_attrs:
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
        """Iterate over schema nodes."""
        return iter(self._schema)

    def __repr__(self) -> str:
        """Show builder schema summary."""
        count = sum(1 for _ in self)
        return f"<{type(self).__name__} ({count} elements)>"

    def __str__(self) -> str:
        """Show schema structure."""
        return str(self._schema)
