# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Contributed builders — ready-to-use domain-specific components.

These are shipped with genro-builders but are not part of the core
framework. They are optional and only loaded when explicitly imported.

Aligned with the current ``BuilderHandler`` contract (post 2026-05-12
renegotiation of decision 8):
    - ``genro_builders.contrib.html`` — HtmlBuilder (W3C HTML5)
    - ``genro_builders.contrib.svg`` — SvgBuilder
    - ``genro_builders.contrib.css`` — CssBuilder (level 1)

Not yet aligned (import succeeds but objects are not functional under
the current contract; candidates for rewrite or archival):
    - ``genro_builders.contrib.xsd``
    - ``genro_builders.contrib.data``

Archived (moved to ``archive/contrib/``; will return under a future
subtask when the framework supports the features they require):
    - ``markdown`` — relied on pointers/reactive store not yet
      implemented; archived 2026-05-12.
"""
