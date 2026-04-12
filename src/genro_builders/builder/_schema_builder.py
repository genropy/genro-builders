# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SchemaBuilder — programmatic schema creation for builders.

Use SchemaBuilder to define schemas at runtime instead of using decorators.
Creates schema nodes with the structure expected by BagBuilderBase.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import BagBuilderBase

if TYPE_CHECKING:
    from genro_bag import BagNode


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
        schema.builder.save_schema('schema.msgpack')
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

    def save_schema(self, destination: str | Path) -> None:
        """Save schema to MessagePack file for later loading by builders.

        Args:
            destination: Path to the output .msgpack file.
        """
        msgpack_data = self._bag.to_tytx(transport="msgpack")
        Path(destination).write_bytes(msgpack_data)  # type: ignore[arg-type]
