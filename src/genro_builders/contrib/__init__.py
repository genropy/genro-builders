# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Contributed builders — ready-to-use domain-specific components.

These are shipped with genro-builders but are not part of the core
framework. They are optional and only loaded when explicitly imported.

Dialects with a grammar (concrete builders, instantiated by users):
    - ``genro_builders.contrib.html`` — HtmlBuilder (W3C HTML5)
    - ``genro_builders.contrib.svg`` — SvgBuilder
    - ``genro_builders.contrib.css`` — CssBuilder (level 1)
    - ``genro_builders.contrib.xslt`` — XsltBuilder (XSLT 1.0 stylesheets)
    - ``genro_builders.contrib.xsd`` — XsdBuilder (XSD 1.0 schemas)
    - ``genro_builders.contrib.config`` — ConfigBuilder + ConfigHandler
      (configuration trees, distributed grammars)

The abstract XML base and the schema transpiler live in the core
(``genro_builders.xml``), not here: they are bases, not dialects.

Archived (a copy sits in ``temp/archive/contrib/``, a non-distributed
working folder):
    - ``markdown`` — written against machinery that predates the
      current static core; archived 2026-05-12, to be rebuilt on it.
"""
