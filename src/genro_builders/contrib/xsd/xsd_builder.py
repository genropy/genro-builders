# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""XsdBuilder - Dynamic builder generated from XSD schema at runtime.

Creates a builder by parsing an XSD schema file using XsdReader.
The resulting schema is used by BagBuilderBase for validation during
document construction.

Example:
    >>> from genro_builders import BuilderBag
    >>> from genro_builders.contrib.xsd import XsdBuilder
    >>>
    >>> bag = BuilderBag(builder=XsdBuilder, builder_xsd_source='pain.001.001.12.xsd')
    >>> doc = bag.Document()
    >>> # ... build document ...
    >>> bag.builder.build()
    >>> xml = bag.builder.render()  # validates against XSD
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from genro_bag import Bag

from genro_builders.builder import BagBuilderBase, SchemaBuilder

from .xsd_reader import XsdReader

if TYPE_CHECKING:
    pass


class XsdBuilder(BagBuilderBase):
    """Builder dynamically generated from XSD schema at runtime.

    Parses an XSD file using XsdReader and generates a schema
    compatible with BagBuilderBase. Supports optional full XSD validation
    at compile time using xmlschema library.
    """

    def __init__(self, bag: Bag, xsd_source: str | Path):
        """Initialize builder from XSD file path or URL.

        Args:
            bag: The Bag instance this builder is attached to.
            xsd_source: Path to XSD file or URL to fetch XSD from.
        """
        self._xsd_source = xsd_source

        # Create reader based on source type
        path_str = str(xsd_source)
        if path_str.startswith(("http://", "https://")):
            reader = XsdReader.from_url(path_str)
        else:
            reader = XsdReader.from_file(xsd_source)

        # Generate schema from XSD elements
        from genro_builders.builder_bag import BuilderBag

        schema_bag = BuilderBag(builder=SchemaBuilder)
        for name, sub_tags, cav in reader.iter_elements():
            attrs: dict[str, Any] = {"sub_tags": sub_tags}
            if cav:
                attrs["call_args_validations"] = cav
            schema_bag.builder.item(name, **attrs)

        super().__init__(bag)
        self._schema = schema_bag
        self._schema_tag_names = frozenset(
            node.label for node in self._schema.nodes
            if not node.label.startswith("@")
        )

    def _compile(self, full_validate: bool = False) -> str:
        """Compile the bag to XML.

        Args:
            full_validate: If True, validate the output against the original
                XSD schema using xmlschema library.
                Requires xmlschema to be installed.

        Returns:
            The compiled XML document as string.

        Raises:
            ImportError: If full_validate=True but xmlschema is not installed.
            xmlschema.XMLSchemaValidationError: If validation fails.
        """
        result = self._bag.to_xml()

        if full_validate:
            self._validate_with_xsd(result)

        return result

    def _validate_with_xsd(self, xml_content: str) -> None:
        """Validate XML content against the original XSD schema.

        Args:
            xml_content: The XML string to validate.

        Raises:
            ImportError: If xmlschema is not installed.
            xmlschema.XMLSchemaValidationError: If validation fails.
        """
        try:
            import xmlschema  # type: ignore[import-not-found]
        except ImportError as err:
            raise ImportError(
                "xmlschema is required for full_validate. "
                "Install with: pip install genro-bag[xsd-validate]"
            ) from err

        schema = xmlschema.XMLSchema(str(self._xsd_source))
        schema.validate(xml_content)
