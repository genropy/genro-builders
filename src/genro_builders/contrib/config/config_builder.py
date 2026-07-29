# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ConfigBuilder — configuration dialect for genro-builders (v1).

A configuration is a document whose grammar is DISTRIBUTED in the
classes that consume it: the host dialect declares the layout
(``configuration`` root, its sections, the explicit collections), and
each mounted application brings its own grammar as the value of the
``app=`` parameter (subbuilder by reference, contract BLD.2).

The v1 layout is deliberately small — ``server`` plus the explicit
``applications`` collection. A project extends it by subclassing, as
everywhere in builders. Every path in the tree is stable and
hand-writable: ``configuration.server``,
``configuration.applications.<code>``.

Authoring conventions the grammar itself demonstrates:

- section attributes are ANNOTATED, so their signature defaults reach
  the read stack of :class:`~genro_builders.contrib.config.handler.ConfigHandler`
  (an unannotated parameter never enters ``call_args_validations``);
- an attribute whose value may come from outside (env, file, url) is
  annotated ``str | BagResolver`` and receives a resolver IN PLACE —
  no pointers in configuration grammars.

Reading is NOT the builder's job: the recipe produces the source, the
``ConfigHandler`` is the single door the runtime reads it from.
"""

from __future__ import annotations

from genro_bag import BagResolver

from ...builder import BuilderBase, element


class ConfigBuilder(BuilderBase):
    """Configuration dialect: layout grammar only, reading on ``ConfigHandler``."""

    _name = "config"
    _default_render_mode = "xml"

    @element(sub_tags="server[0:1],applications[0:1]", node_label="configuration")
    def configuration(self):
        """Root element of the configuration document (one per recipe)."""
        ...

    @element(parent_tags="configuration")
    def server(self, host: str | BagResolver = None, port: int = 8000):
        """The server section: at most one, stable label ``server``."""
        ...

    @element(parent_tags="configuration", sub_tags="application", collection_key="code")
    def applications(self):
        """Explicit collection of applications, each labelled by its ``code``."""
        ...

    @element(parent_tags="applications", _meta={"subbuilder": "app:grammar"})
    def application(self, code: str, app=None):
        """Mount point: ``app`` carries the grammar class of the subtree."""
        ...
