# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XsdReader — import an existing .xsd into an XsdBuilder source tree.

The reverse of rendering: parse a schema written by someone else and
rebuild it inside a builder, node for node, exactly as if the schema had
been written with ``root.schema().element()...``. The populated source
tree is then the single pivot — render it back to ``.xsd`` (to check the
import is faithful) or emit the ``.py`` that recreates it.

Parser is the standard-library ``ElementTree`` (no new dependency): it
preserves structure, attributes verbatim, and namespaces (in Clark form
``{uri}local``), which is all a structure-faithful import needs. It does
not preserve comments or the original prefixes — irrelevant for
equipollence (the reproduced schema validates the same documents), not
byte-identity.

Grammar-parametric (contract choice): the reader is given a builder and
uses THAT builder's grammar to resolve every tag. So the same reader
imports a pure XSD with :class:`XsdBuilder`, and an XSD carrying an
``<editor>`` application vocabulary with a downstream ``GnrXsdBuilder``
that declares ``editor``. A tag the given grammar does not know is a
loud error (no silent preservation): pass the grammar that covers the
document, or the input is out of contract.

The ``xmlns`` binding of the ``xs`` prefix is re-added on the schema
root as ``xmlns_xs`` so the rendered output re-declares it; XSD attribute
values that carry a prefix (``type="xs:string"``) are opaque strings to
ElementTree and ride through verbatim.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


XS_URI = "http://www.w3.org/2001/XMLSchema"


class XsdReader:
    """Populate a builder's source tree from an existing XSD document.

    Construction is cheap. :meth:`read` does the parse and returns the
    builder with its source tree populated (ready to render or emit).
    """

    def __init__(self, builder: Any) -> None:
        """``builder`` is the XsdBuilder (or subclass) whose grammar drives
        tag resolution and whose source tree is populated. Stored as
        ``self.builder`` per the parent-passes-self convention."""
        self.builder = builder

    def read(self, source: str | Path) -> Any:
        """Parse ``source`` (a path or an XSD string) and populate the
        builder's source tree. Return the builder.

        The reader IS the builder's recipe: instead of a hand-written
        ``main``, the walk populates the tree. It installs that walk as the
        instance ``main`` and calls ``create()``, so the walk runs exactly
        where ``create`` would have run ``main`` — the tree is built
        through the normal grammar entry points.
        """
        root_el = self._parse(source)
        # Application namespaces met during the walk, prefix -> uri, keyed
        # by the grammar's own ``ns`` for the tag. Re-declared as
        # ``xmlns_<prefix>`` on the schema root so the render re-emits the
        # binding ElementTree consumed into Clark notation.
        self._app_ns: dict[str, str] = {}
        self._root_node: Any = None
        # Top level: parent is the builder's source Bag; deeper levels:
        # parent is the node just created. ``parent_node=None`` marks the
        # Bag-root case.
        self.builder.main = lambda root: self._build(root_el, parent_node=None)
        self.builder.create()
        self._declare_app_namespaces()
        return self.builder

    def _declare_app_namespaces(self) -> None:
        """Add ``xmlns_<prefix>`` for every application namespace met, on
        the schema root — the same author form (``xmlns_ed`` -> ``xmlns:ed``)
        a hand-written recipe would use."""
        if self._root_node is None:
            return
        for prefix, uri in self._app_ns.items():
            self._root_node.set_attr(**{f"xmlns_{prefix}": uri})

    # ------------------------------------------------------------------

    def _parse(self, source: str | Path) -> ET.Element:
        """Parse a path or a raw XSD string into an ElementTree element."""
        if isinstance(source, Path):
            return ET.fromstring(Path(source).read_text())
        if not source.lstrip().startswith("<"):
            return ET.fromstring(Path(source).read_text())
        return ET.fromstring(source)

    def _build(self, el: ET.Element, parent_node: Any) -> None:
        """Create the node for ``el`` under ``parent_node`` and recurse.

        The tag ``{uri}local`` is split; ``local`` is resolved against the
        builder's grammar. The ``xs`` prefix binding is re-added on the
        root element so the render re-declares ``xmlns:xs``. The same two
        grammar entry points the user's ``main`` goes through are used:
        ``_bag_call`` on the source Bag for the root element,
        ``_command_on_node`` on a node for every child.
        """
        uri, local = self._split_tag(el.tag)
        node_tag = self._resolve_tag(local)

        attrs = dict(el.attrib)
        if uri == XS_URI and local == "schema" and "xmlns_xs" not in attrs:
            attrs["xmlns_xs"] = XS_URI

        node_value = (el.text or "").strip() or None

        if parent_node is None:
            call = self.builder._bag_call(self.builder.source, node_tag)
            node = call(node_value, **attrs) if node_value else call(**attrs)
            self._root_node = node
        else:
            node = self.builder._command_on_node(
                parent_node, node_tag, *( (node_value,) if node_value else () ),
                **attrs,
            )

        # An application-namespace tag (uri other than XSD): record its
        # grammar prefix -> uri so the root re-declares the binding.
        if uri and uri != XS_URI:
            prefix = node.get_attr("ns")
            if prefix:
                self._app_ns[prefix] = uri

        for child in el:
            self._build(child, node)

    def _split_tag(self, tag: str) -> tuple[str, str]:
        """Split an ElementTree ``{uri}local`` tag into ``(uri, local)``.
        A tag with no namespace returns ``("", tag)``."""
        if tag.startswith("{"):
            uri, _, local = tag[1:].partition("}")
            return uri, local
        return "", tag

    def _resolve_tag(self, local: str) -> str:
        """Resolve an XSD local name to the builder's schema tag.

        Direct match first; then the Python-keyword form ``<local>_``
        (``import`` -> ``import_``). A name the grammar does not know is a
        loud error — pass a grammar that covers the document."""
        names = self.builder._schema_tag_names
        tag = names.get(local.lower())
        if tag is not None:
            return tag
        tag = names.get(f"{local}_".lower())
        if tag is not None:
            return tag
        raise ValueError(
            f"tag {local!r} is not in the grammar of "
            f"{type(self.builder).__name__!r}; pass a builder whose grammar "
            f"covers this document (e.g. a downstream dialect that declares it)"
        )


if __name__ == "__main__":
    from genro_builders.contrib.xsd import XsdBuilder

    XSD = (
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" '
        'targetNamespace="urn:demo" elementFormDefault="qualified">'
        '<xs:element name="Person"><xs:complexType><xs:sequence>'
        '<xs:element name="Name" type="xs:string"/>'
        '<xs:element name="Age" type="xs:integer" minOccurs="0"/>'
        '</xs:sequence></xs:complexType></xs:element>'
        '<xs:import namespace="urn:ext" schemaLocation="ext.xsd"/>'
        "</xs:schema>"
    )

    builder = XsdReader(XsdBuilder()).read(XSD)
    print(builder.render(target=False, doc_header=True, pretty=True))
