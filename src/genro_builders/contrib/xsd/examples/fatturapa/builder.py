# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""FatturaPABuilder — concrete dialect for the Italian PA electronic invoice.

The grammar comes from :class:`FatturaPAElements`, generated from the
official ``Schema_VFPA12_V1.2.3.xsd`` published by Agenzia delle
Entrate. Rendering uses the inherited XML renderer (``mode="xml"``):
there is no FatturaPA-specific renderer because the on-the-wire
format is plain XML.

This dialect is **not** registered under a canonical ``_name``: it is
meant to be used as an example of the codegen pipeline, not as a
shared sub-builder reachable via ``@subbuilder("fatturapa")``.
Downstream code that needs FatturaPA construction imports
:class:`FatturaPABuilderHandler` directly.
"""

from __future__ import annotations

from genro_builders.builder import BagBuilderBase
from genro_builders.builder_handler import BuilderHandler
from genro_builders.contrib.xsd.examples.fatturapa.fatturapa_elements import (
    FatturaPAElements,
)


class FatturaPABuilder(BagBuilderBase, FatturaPAElements):
    """FatturaPA dialect builder. Grammar comes from the generated
    ``FatturaPAElements`` mixin."""

    _default_render_mode = "xml"


class FatturaPABuilderHandler(BuilderHandler):
    """Preset handler bound to :class:`FatturaPABuilder` (decision 9 v0.4.0)."""

    builder_class = FatturaPABuilder
