# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CSS element definitions — level 1 grammar (selector-first model).

Selector is the top-level "case" container. Each selector groups
rules (each rule is the property block; multiple rules under one
selector are merged by the renderer, grouped by their optional
``media`` / ``supports`` kwargs).

Six elements:

- ``stylesheet`` — optional top-level container holding selectors,
  selector lists, global cssvars, and ``@import`` directives.
- ``selector`` — a single CSS selector. Holds the rule(s), the
  cssvar declarations, and any nested ``selector`` for CSS
  Nesting.
- ``selectorList`` — explicit container for a selector-list
  (comma-separated). Holds N ``selector`` children plus the
  ``rule`` / ``cssvar`` of the shared block.
- ``rule`` — the property block of a selector or selectorList.
  Optional ``media`` / ``supports`` kwargs lift the rule into a
  ``@media`` / ``@supports`` block at render time. Multiple rules
  under the same selector are grouped by ``(media, supports)``.
- ``cssvar`` — a CSS custom property declaration (``--name:
  value;``). Lives inside a selector or selectorList, or directly
  under ``stylesheet`` / bag root (in which case the renderer
  emits an implicit ``:root { ... }`` block).
- ``importcss`` — a CSS ``@import`` directive. Lives only inside
  ``stylesheet``; rendered before any other content of the
  stylesheet to honour the CSS rule that ``@import`` must precede
  every other at-rule and selector.

Other at-rules (``@keyframes``, ``@font-face``, ``@property``,
``@layer`` block-form, ``@scope``, ...) are out of scope for
level 1.

Property naming on ``rule``: kebab-case CSS properties
(``font-size``, ``background-color``) are passed as kwargs with
underscores. The renderer converts underscores back to hyphens
at emit time.
"""

from __future__ import annotations

from genro_builders.builder import element


class CssElements:
    """Mixin defining the level-1 CSS grammar for CssBuilder."""

    @element(sub_tags="selector,selectorList,cssvar,importcss")
    def stylesheet(self):
        """Top-level container holding the whole CSS document.

        A stylesheet is the optional "shell" that groups every other
        top-level construct. Using it is mandatory only when the
        document includes ``@import`` directives, since those have to
        live inside a stylesheet by grammar; in every other case the
        stylesheet is optional and ``selector`` / ``selectorList`` /
        ``cssvar`` children can sit directly on the bag root.

        **Kwargs**:

        - ``comment`` (optional, str) — free-form comment text emitted
          inline or as a block depending on length. **Not validated**.

        **Children allowed**: ``selector``, ``selectorList``,
        ``cssvar``, ``importcss``.

        **Grammar position**: top-level only. Cannot be nested inside
        another stylesheet, a selector, a rule, etc.

        **Render order**: the renderer emits ``importcss`` children
        first (CSS requires ``@import`` to precede every other
        directive), then ``cssvar`` declarations as a single implicit
        ``:root { ... }`` block, then ``selector`` / ``selectorList``
        blocks in insertion order.

        **What we validate**: the parent container (bag root only)
        and the set of allowed children listed above.
        **What we do not validate**: the semantic correctness of the
        children themselves (each child has its own validation).
        """
        ...

    @element(sub_tags="rule,cssvar,selector")
    def selector(self):
        """A single CSS selector. The case container.

        Built from structured kwargs (``tag``, ``id``, ``class_``,
        ``classes``, ``attr``) and/or an opaque ``raw`` suffix.
        Holds one or more ``rule`` children (the base block plus
        any media/supports variants), ``cssvar`` declarations, and
        nested ``selector`` elements (CSS Nesting)."""
        ...

    @element(sub_tags="selector,rule,cssvar")
    def selectorList(self):
        """Container for a comma-separated selector-list.

        Use when the same rule(s) apply to more than one selector.
        Holds N ``selector`` children plus the ``rule`` /
        ``cssvar`` of the shared block."""
        ...

    @element(sub_tags="")
    def rule(self):
        """The property block of a selector or selectorList.

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

    @element(sub_tags="")
    def importcss(self):
        """A CSS ``@import`` directive — pull an external stylesheet
        into the current document.

        ``@import`` is the standard CSS mechanism for splitting a
        stylesheet across multiple source files. The browser fetches
        the referenced sheet and merges its content into the current
        one. The directive must appear *before* any selector or other
        at-rule in the document, otherwise browsers silently ignore
        it; this constraint is enforced by the renderer (importcss
        children of a stylesheet are emitted first, in insertion
        order).

        **Kwargs**:

        - ``url`` (required, str) — the URL of the imported sheet.
          Emitted as ``@import url("<url>");``. The string is passed
          verbatim and wrapped in double quotes; **the URL itself is
          not validated** (any protocol, path, query string, or
          unicode the user wants is accepted as-is — quoting any
          ``"`` inside is the caller's responsibility).
        - ``media`` (optional, str) — a media query that scopes the
          imported sheet (``@import url(...) <media-query>;``).
          Free-form string passed verbatim. **Not validated**.
        - ``supports`` (optional, str) — a feature query attached to
          the import (``@import url(...) supports(<condition>);``).
          Pass the condition **with its own parentheses**, mirroring
          the ``supports`` kwarg on ``rule`` (e.g.
          ``supports="(display: grid)"``). The renderer only
          prepends the ``supports`` keyword. Free-form, verbatim.
          **Not validated**.
        - ``layer`` (optional, str) — a cascade-layer name
          (``@import url(...) layer(<name>);``). Pass an empty string
          to emit ``layer`` without an argument (the anonymous-layer
          form). Free-form string passed verbatim. **Not validated**.
        - ``comment`` (optional, str) — free-form comment text emitted
          inline or as a block before the directive depending on
          length. **Not validated**.

        **Grammar position**: child of ``stylesheet`` only. Cannot be
        placed under a ``selector``, ``rule``, ``selectorList`` or
        directly on the bag root — open a ``stylesheet`` first.

        **Render order**: the renderer emits all ``importcss``
        children of a ``stylesheet`` *before* any selector,
        selectorList, or cssvar block, in their insertion order.

        **Render syntax**: when multiple optional kwargs are present
        the order is fixed as
        ``@import url("<url>") layer(...) supports(...) <media-query>;``.
        That mirrors the order mandated by the CSS spec
        (``@import <url> <layer>? <supports>? <media-query-list>?;``).

        **What we validate**: the parent container (must be
        ``stylesheet``) and presence of ``url``.
        **What we do not validate**: the URL itself, the media query
        syntax, the supports condition syntax, the layer name
        syntax.
        """
        ...
