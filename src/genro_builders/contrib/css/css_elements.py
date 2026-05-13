# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CSS element definitions — level 1 grammar.

Four elements:

- ``stylesheet`` — optional top-level container holding a list of
  rules.
- ``rule`` — a CSS rule: a selector-list plus property declarations.
  Allowed both inside ``stylesheet`` and directly at the bag root,
  so the builder can produce fragments as well as full stylesheets.
  Selectors are declared via ``selector`` children (1..N: multiple
  children become a comma-separated selector-list).
- ``selector`` — declares a single entry of the rule's selector-list.
  Built from kwargs (``tag``, ``id``, ``_class``, ``classes``,
  ``attr``, ``raw``). Validated by the renderer with regexes; ``raw``
  is the unchecked escape hatch for combinators and anything not
  covered by the structured kwargs.
- ``cssvar`` — a CSS custom property declaration
  (``--name: value;``). Lives inside a rule.

At-rules (``@media``, ``@keyframes``, ``@supports``, ...) and rule
nesting are out of scope for level 1.

Property naming on ``rule``: kebab-case CSS properties
(``font-size``, ``background-color``) are passed as kwargs with
underscores (``font_size``, ``background_color``). The renderer
converts the underscores back to hyphens at emit time.

Fluent chaining with ``._``: a leaf element call (``selector(...)``
or ``cssvar(...)``) returns the leaf node, which carries the
genro-bag ``._`` property pointing back at the containing bag.
That lets the rule body be expressed as a single chain::

    root.rule(color="red", font_size="14px") \\
        .selector(_class="card")._ \\
        .selector(_class="panel")._ \\
        .cssvar("primary", value="#3498db")

The equivalent non-chained form (assign the rule to a variable
and call methods on it) stays valid; choose whichever reads
better in context.
"""

from __future__ import annotations

from genro_builders.builder import element


class CssElements:
    """Mixin defining the level-1 CSS grammar for CssBuilder."""

    @element(sub_tags="rule")
    def stylesheet(self):
        """Top-level container for a list of CSS rules."""
        ...

    @element(sub_tags="selector,cssvar,rule")
    def rule(self):
        """A CSS rule: selector-list (via ``selector`` children) plus
        property declarations (via kwargs). Rules can be nested:
        adding a child ``rule`` produces native CSS nesting in the
        rendered output."""
        ...

    @element(sub_tags="")
    def selector(self):
        """A single entry of a rule's selector-list. Built from
        structured kwargs (``tag``, ``id``, ``_class``, ``classes``,
        ``attr``) and/or an opaque ``raw`` suffix.

        Placement is constrained by ``rule.sub_tags``; the framework
        validates from the parent side, so ``parent_tags`` here would
        be redundant (and would fail to match the rule's sub-bag's
        missing ``_parent_node`` slot)."""
        ...

    @element(sub_tags="")
    def cssvar(self):
        """A CSS custom property declaration (``--name: value;``).
        Placement constraint flows from ``rule.sub_tags``."""
        ...
