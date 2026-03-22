# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderBag and BuilderBagNode - Bag subclasses with builder support.

BuilderBag extends Bag to support domain-specific builders that define
grammars for creating nodes. BuilderBagNode extends BagNode to delegate
attribute access to the builder.

Example:
    >>> from genro_builders import BuilderBag
    >>> from genro_builders.builders import HtmlBuilder
    >>> html = BuilderBag(builder=HtmlBuilder)
    >>> html.div(id='main').p(value='Hello')
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode
from genro_toolbox.decorators import extract_kwargs


class BuilderBagNode(BagNode):
    """BagNode with builder delegation.

    When a builder is attached to the parent Bag, allows calling
    builder methods directly on nodes to add children:

        node = bag.div()  # returns BuilderBagNode
        node.span()       # delegates to builder._command_on_node()
    """

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to builder if available."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        builder = self._parent_bag._builder if self._parent_bag is not None else None

        if builder is not None:
            return lambda node_value=None, node_position=None, **attrs: builder._command_on_node(
                self, name, node_position=node_position, node_value=node_value, **attrs
            )

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


class BuilderBag(Bag):
    """Bag with builder support.

    Extends Bag to accept a builder class that defines a grammar for
    creating nodes with validation, schema constraints, and compilation.

    Attributes:
        node_class: Uses BuilderBagNode for builder-aware nodes.
        _builder: The BagBuilderBase instance attached to this bag.
    """

    node_class: type[BagNode] = BuilderBagNode

    @extract_kwargs(builder=True)
    def __init__(
        self,
        source: dict[str, Any] | None = None,
        builder: Any = None,
        builder_kwargs: dict | None = None,
    ):
        """Create a new BuilderBag.

        Args:
            source: Optional dict to initialize from.
            builder: Optional BagBuilderBase class for domain-specific
                node creation (e.g., HtmlBuilder for HTML generation).
            builder_kwargs: Extra kwargs passed to builder constructor.
                Can also be passed with builder_ prefix.
        """
        super().__init__(source=source)
        self._builder = builder(self, **builder_kwargs) if builder else None

    @property
    def builder(self) -> Any:
        """Get the builder associated with this Bag."""
        return self._builder

    @builder.setter
    def builder(self, value: Any) -> None:
        """Set the builder for this Bag."""
        self._builder = value

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to builder if present.

        When a builder is set, delegates to builder._bag_call() which handles
        both schema elements and builder methods/properties.
        """
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        if self._builder is not None:
            return self._builder._bag_call(self, name)

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
