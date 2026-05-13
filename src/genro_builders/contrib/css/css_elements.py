# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CSS element definitions — level 1 grammar (selector-first model).

Selector is the top-level "case" container. Each selector groups a
rule (properties) and any number of variants (media, supports,
nested selectors).

Five elements:

- ``stylesheet`` — optional top-level container holding selectors,
  selector lists, and global cssvars.
- ``selector`` — a single CSS selector. Holds the rule (properties)
  and the variants. Can host nested selectors for CSS Nesting.
- ``selector_list`` — explicit container for a selector-list
  (comma-separated). Use when more than one selector shares the
  same rule and variants. Holds N ``selector`` children plus the
  rule/media/supports/cssvar of the shared block.
- ``rule`` — the property block of a selector or selector_list.
  Properties are passed as kwargs (kebab-case via underscores).
  Holds nothing.
- ``media`` — a media-query variant. Properties as kwargs apply to
  the parent selector inside the @media block. Can host nested
  selectors for sub-selectors inside the media query.
- ``supports`` — same shape as ``media`` but with a @supports
  condition.
- ``cssvar`` — a CSS custom property declaration (``--name:
  value;``). Lives inside a selector or selector_list.

At-rules other than @media/@supports (``@keyframes``,
``@font-face``, ``@import``, ``@property``, ...) are out of scope
for level 1.

Property naming on ``rule`` / ``media`` / ``supports``: kebab-case
CSS properties (``font-size``, ``background-color``) are passed
as kwargs with underscores. The renderer converts underscores
back to hyphens at emit time.

Selector kwargs and the structured-vs-raw distinction are
documented on ``selector`` itself.
"""

from __future__ import annotations

from genro_builders.builder import element


class CssElements:
    """Mixin defining the level-1 CSS grammar for CssBuilder."""

    @element(sub_tags="selector,selector_list,cssvar")
    def stylesheet(self):
        """Top-level container holding selectors and global cssvars."""
        ...

    @element(sub_tags="rule,media,supports,cssvar,selector")
    def selector(self):
        """A single CSS selector. The case container.

        Built from structured kwargs (``tag``, ``id``, ``_class``,
        ``classes``, ``attr``) and/or an opaque ``raw`` suffix.
        Holds a ``rule`` (properties), ``media`` / ``supports``
        variants, ``cssvar`` declarations, and nested ``selector``
        elements (CSS Nesting)."""
        ...

    @element(sub_tags="selector,rule,media,supports,cssvar")
    def selector_list(self):
        """Container for a comma-separated selector-list.

        Use when the same rule/variants apply to more than one
        selector. Holds N ``selector`` children plus the
        ``rule``/``media``/``supports``/``cssvar`` of the shared
        block."""
        ...

    @element(sub_tags="")
    def rule(self):
        """The property block of a selector or selector_list.

        Properties are passed as kwargs; underscores are converted
        to hyphens in the output."""
        ...

    @element(sub_tags="selector,rule")
    def media(self):
        """A @media variant of the parent selector.

        Pass the media condition as ``condition="..."`` (e.g.
        ``condition="(max-width: 600px)"``). Property kwargs apply
        to the parent selector inside the @media block. Can host
        nested ``selector`` and ``rule`` for sub-selectors inside
        the media query."""
        ...

    @element(sub_tags="selector,rule")
    def supports(self):
        """A @supports variant of the parent selector.

        Pass the supports condition as ``condition="..."`` (e.g.
        ``condition="(display: grid)"``). Property kwargs apply to
        the parent selector inside the @supports block."""
        ...

    @element(sub_tags="")
    def cssvar(self):
        """A CSS custom property declaration (``--name: value;``)."""
        ...
