# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Renderer package — the universal walk base plus the core render modes.

``RendererBase`` owns the walk + cache + finalize; concrete dialects
subclass it (in contrib) and implement ``rendered_item``. The two render
modes shared by every builder live here: ``XmlRenderer`` (always
available) and ``YamlRenderer`` (PyYAML-gated). External imports go
through this facade (``from genro_builders.renderer import X``); internal
code imports the concrete module directly to avoid load-order cycles.
"""

from .base import RendererBase
from .xml import XmlRenderer
from .yaml import YamlRenderer

__all__ = [
    "RendererBase",
    "XmlRenderer",
    "YamlRenderer",
]
