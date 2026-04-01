# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Built-in renderers for genro-builders."""

from genro_builders.compilers.yaml_compiler import YamlRendererBase

# Legacy alias
YamlCompilerBase = YamlRendererBase

__all__ = ["YamlCompilerBase", "YamlRendererBase"]
