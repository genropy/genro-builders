# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Contributed builders — ready-to-use domain-specific components.

These are shipped with genro-builders but are not part of the core
framework. They are optional and only loaded when explicitly imported.

In scope during the 2026-05 restart:
    - ``genro_builders.contrib.html`` — HtmlBuilder (W3C HTML5)

Dormant during the restart (do not import — pending migration to the
new BuilderHandler contract):
    - ``genro_builders.contrib.markdown`` — raises ImportError on import
    - ``genro_builders.contrib.svg`` — raises ImportError on import
    - ``genro_builders.contrib.xsd`` — imports succeed but objects are
      not functional under the new contract
    - ``genro_builders.contrib.data`` — imports succeed but objects are
      not functional under the new contract
"""
