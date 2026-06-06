# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CssBuilder — CSS dialect for genro-builders (level 1).

Level 1 grammar covers ``stylesheet``, ``selector``, ``selector_list``,
``rule`` (property declarations with optional ``media`` / ``supports``
kwargs), ``cssvar`` (CSS custom property declarations) and
``importcss`` (``@import`` directives). At-rules beyond ``@media`` /
``@supports`` / ``@import`` (``@keyframes``, ``@font-face``,
``@property``, ``@layer`` block-form, ``@scope``, ...) are out of
scope and will be handled by a dedicated future subtask.

The grammar lives in ``CssElements``. Rendering lives on
``CssRenderer`` (``render_css`` method). Compilation (future) lives
on ``CssCompiler``. The builder only wires them together
(decision 8, renegotiated 2026-05-12).

The class also exposes the two reverse classmethods ``from_css`` and
``from_css_file``: see their docstrings for the documented exception
to the "no classmethod" rule of the project.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from ...builder import BuilderBase
from .css_elements import CssElements
from .css_renderer import CssRenderer


class CssBuilder(BuilderBase, CssElements):
    """CSS dialect builder. Grammar only — rendering on
    ``CssRenderer``, exposed via the ``renderer_css`` property."""

    _name = "css"
    _default_render_mode = "css"

    @property
    def renderer_css(self) -> CssRenderer:
        """Fresh ``CssRenderer`` instance bound to this builder.

        Each access returns a new instance: the renderer is meant to be
        ephemeral, used for a single ``render`` call and discarded.
        """
        return CssRenderer(builder=self)

    # ------------------------------------------------------------------
    # Reverse: from CSS source to CssBuilderHandler Python source
    # ------------------------------------------------------------------
    #
    # The two reverse entry points are declared as classmethods on the
    # builder, in a conscious exception to the project-wide "no
    # classmethod" rule. The rationale is API ergonomics: the reverse
    # is invoked before any builder instance exists (it produces the
    # code that will *later* be used to build the bag), so the natural
    # call site is ``CssBuilder.from_css(...)`` / ``from_css_file(...)``
    # rather than ``CssBuilder().from_css(...)`` which would suggest an
    # instance-bound operation that does not exist.
    #
    # The ``dest`` parameter mirrors the renderer convention
    # implemented in ``RendererBase._write_or_return``: ``None`` returns
    # the string, ``str``/``Path`` writes to filesystem (parent dirs
    # created if missing), file-like with ``.write`` is written to,
    # callable is invoked with the text. The forwarding is direct: we
    # build an ephemeral renderer instance just to reuse that helper.

    @classmethod
    def from_css(
        cls,
        source: str,
        dest: Any = None,
        *,
        class_name: str = "ReversedCss",
    ) -> str | None:
        """Parse a CSS string and emit equivalent CssBuilder Python.

        The output is a complete Python module containing an
        ``import`` line for ``CssBuilderHandler`` and a subclass
        named ``class_name`` whose ``main(self, root)`` rebuilds the
        input CSS via the builder API. The emitted ``main`` always
        opens a ``root.stylesheet()`` as its first statement.

        :param source: CSS source text.
        :param dest: destination for the generated Python source. See
            ``RendererBase._write_or_return`` for accepted shapes:
            ``None`` returns the string, ``str``/``Path`` writes to a
            file, file-like or callable consume the text. When ``dest``
            is provided this method returns ``None``.
        :param class_name: name of the generated subclass. Defaults to
            ``"ReversedCss"``.
        :returns: the Python source as a string when ``dest is None``,
            otherwise ``None`` (the text has been written to ``dest``).
        :raises ImportError: the optional ``[reverse]`` extra is not
            installed (``tree-sitter-css`` missing).

        Requires the optional ``reverse`` extra::

            pip install 'genro-builders[reverse]'
        """
        from .transpiler import CssTranspiler

        module = CssTranspiler(class_name=class_name).transpile(source)
        text = ast.unparse(module)
        return _emit(text, dest)

    @classmethod
    def from_css_file(
        cls,
        path: str | Path,
        dest: Any = None,
        *,
        class_name: str | None = None,
    ) -> str | None:
        """Read a CSS file and emit equivalent CssBuilder Python.

        Convenience wrapper around ``from_css``: reads ``path`` as
        UTF-8 text and delegates. When ``class_name`` is ``None`` the
        name is derived from the file stem via
        :func:`_class_name_from_stem`: if the stem starts with a digit
        the leading numeric segment is dropped (split on ``_``), the
        remaining segments are CamelCased, and the suffix ``Style`` is
        appended. Examples::

            theme.css            -> ThemeStyle
            00_gnr_resets.css    -> GnrResetsStyle
            02b_gnr_icons_svg    -> GnrIconsSvgStyle

        If the derived name would be empty (the stem is a single
        digit-only segment or is empty), the fallback is ``Style``.

        :param path: filesystem path to the input CSS.
        :param dest: see ``from_css``.
        :param class_name: optional override; default is the value
            returned by :func:`_class_name_from_stem`.
        :returns: same contract as ``from_css``.
        :raises ImportError: the optional ``[reverse]`` extra is not
            installed.
        """
        p = Path(path)
        source = p.read_text(encoding="utf-8")
        name = class_name if class_name is not None else _class_name_from_stem(p.stem)
        return cls.from_css(source, dest, class_name=name)


def _class_name_from_stem(stem: str) -> str:
    """Derive a Python-identifier class name from a file stem.

    Rules (see ``CssBuilder.from_css_file`` docstring for examples):

    - if ``stem`` starts with a digit, split on ``_`` and drop the
      first (leading-digit) segment;
    - CamelCase every remaining segment;
    - append the suffix ``Style``;
    - fall back to ``Style`` if nothing usable is left.
    """
    if not stem:
        return "Style"
    parts = stem.split("_")
    if stem[0].isdigit():
        parts = parts[1:]
    parts = [p for p in parts if p]
    if not parts:
        return "Style"
    return "".join(p[0].upper() + p[1:] for p in parts) + "Style"


def _emit(text: str, dest: Any) -> str | None:
    """Apply the ``_write_or_return`` contract without needing a
    full renderer instance. Mirrors ``RendererBase._write_or_return``.
    """
    if dest is None:
        return text
    if isinstance(dest, (str, Path)):
        target = Path(dest)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return None
    write = getattr(dest, "write", None)
    if callable(write):
        write(text)
        return None
    if callable(dest):
        dest(text)
        return None
    raise TypeError(
        f"dest {dest!r} is neither a path (str/Path), writable "
        "(.write), nor callable",
    )
