# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CLI entry point for the XSLT->Python transpiler.

Usage::

    python -m genro_builders.contrib.xslt.transpiler \\
        --xslt path/to/stylesheet.xslt \\
        --handler-name MyStylesheet \\
        --output path/to/my_stylesheet.py

The CLI is intentionally minimal: parse args, read the stylesheet, run
the transpiler, write the file. Phase-2 readability passes belong in a
separate tool, not here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .backend import XsltTranspiler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m genro_builders.contrib.xslt.transpiler",
        description="Transpile an XSLT stylesheet to Python rebuilding it.",
    )
    parser.add_argument(
        "--xslt",
        required=True,
        type=Path,
        help="Path to the XSLT stylesheet file.",
    )
    parser.add_argument(
        "--handler-name",
        default="GeneratedStylesheet",
        help=(
            "Class name of the generated handler (subclasses "
            "XsltBuilderHandler). Defaults to GeneratedStylesheet."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file. If omitted, writes to stdout.",
    )
    args = parser.parse_args(argv)

    xslt_source = args.xslt.read_text(encoding="utf-8")
    source = XsltTranspiler(handler_name=args.handler_name).transpile(xslt_source)

    if args.output is None:
        sys.stdout.write(source)
    else:
        args.output.write_text(source, encoding="utf-8")
        print(f"Wrote {args.output} ({source.count(chr(10))} lines)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
