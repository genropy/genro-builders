# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HTML contrib — under reconstruction (2026-05 restart).

The HTML builder will be rewritten in fase 2 of the 2026-05 restart
to honor the new BuilderHandler contract (decisions 4-6, 9). During
fase 1 the public entry point is intentionally rejected so that no
code accidentally depends on the legacy HtmlManager / HtmlRenderer
shape that fase 2 will replace.
"""

raise ImportError(
    "genro_builders.contrib.html is under reconstruction during fase 1 "
    "of the 2026-05 restart. The new HtmlBuilderHandler will be "
    "introduced in fase 2."
)
