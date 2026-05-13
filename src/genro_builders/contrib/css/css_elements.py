# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CSS element definitions — level 1 grammar (selector-first model).

Selector is the top-level "case" container. Each selector groups
rules (each rule is the property block; multiple rules under one
selector are merged by the renderer, grouped by their optional
``media`` / ``supports`` kwargs).

Four elements:

- ``stylesheet`` — optional top-level container holding selectors,
  selector lists, and global cssvars.
- ``selector`` — a single CSS selector. Holds the rule(s), the
  cssvar declarations, and any nested ``selector`` for CSS
  Nesting.
- ``selector_list`` — explicit container for a selector-list
  (comma-separated). Holds N ``selector`` children plus the
  ``rule`` / ``cssvar`` of the shared block.
- ``rule`` — the property block of a selector or selector_list.
  Optional ``media`` / ``supports`` kwargs lift the rule into a
  ``@media`` / ``@supports`` block at render time. Multiple rules
  under the same selector are grouped by ``(media, supports)``.
- ``cssvar`` — a CSS custom property declaration (``--name:
  value;``). Lives inside a selector or selector_list.

At-rules other than @media/@supports (``@keyframes``,
``@font-face``, ``@import``, ``@property``, ...) are out of scope
for level 1.

Property naming on ``rule``: kebab-case CSS properties
(``font-size``, ``background-color``) are passed as kwargs with
underscores. The renderer converts underscores back to hyphens
at emit time.
"""

from __future__ import annotations

from genro_builders.builder import element


class CssElements:
    """Mixin defining the level-1 CSS grammar for CssBuilder."""

    @element(sub_tags="selector,selector_list,cssvar")
    def stylesheet(self):
        """Top-level container holding selectors and global cssvars."""
        ...

    @element(sub_tags="rule,cssvar,selector")
    def selector(self):
        """A single CSS selector. The case container.

        Built from structured kwargs (``tag``, ``id``, ``_class``,
        ``classes``, ``attr``) and/or an opaque ``raw`` suffix.
        Holds one or more ``rule`` children (the base block plus
        any media/supports variants), ``cssvar`` declarations, and
        nested ``selector`` elements (CSS Nesting)."""
        ...

    @element(sub_tags="selector,rule,cssvar")
    def selector_list(self):
        """Container for a comma-separated selector-list.

        Use when the same rule(s) apply to more than one selector.
        Holds N ``selector`` children plus the ``rule`` /
        ``cssvar`` of the shared block."""
        ...

    @element(sub_tags="")
    def rule(self):
        """The property block of a selector or selector_list.

        Properties are passed as kwargs; underscores are converted
        to hyphens in the output.

        Optional kwargs ``media`` and ``supports`` lift this rule
        into a ``@media`` / ``@supports`` block targeting the
        parent selector(s). Both accept a free-form string with
        the full condition (e.g. ``media="(max-width: 600px)"``,
        ``media="screen and (max-width: 600px)"``,
        ``supports="(display: grid)"``). Multiple rules under the
        same selector that share the same ``(media, supports)``
        pair are merged into a single block."""
        ...

    @element(sub_tags="")
    def cssvar(self):
        """A CSS custom property declaration (``--name: value;``)."""
        ...
