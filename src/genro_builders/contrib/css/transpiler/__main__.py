# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CLI entry point for the CSS->Python transpiler.

Usage::

    python -m genro_builders.contrib.css.transpiler \\
        --css path/to/styles.css \\
        --class-name MyStyle \\
        --output path/to/my_style.py

The CLI is intentionally minimal: parse args, read the stylesheet, run
the transpiler, write the file. When ``--class-name`` is omitted the
name is derived from the file stem (see ``CssBuilder.from_css_file``).
Requires the optional ``reverse`` extra (``tree-sitter-css``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..css_builder import CssBuilder


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m genro_builders.contrib.css.transpiler",
        description="Transpile a CSS stylesheet to Python rebuilding it.",
    )
    parser.add_argument(
        "--css",
        required=True,
        type=Path,
        help="Path to the CSS stylesheet file.",
    )
    parser.add_argument(
        "--class-name",
        default=None,
        help=(
            "Class name of the generated handler (subclasses "
            "CssBuilderHandler). Defaults to a name derived from the "
            "file stem."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file. If omitted, writes to stdout.",
    )
    args = parser.parse_args(argv)

    source = CssBuilder.from_css_file(args.css, class_name=args.class_name)

    if args.output is None:
        sys.stdout.write(source)
    else:
        args.output.write_text(source, encoding="utf-8")
        print(f"Wrote {args.output} ({source.count(chr(10))} lines)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
