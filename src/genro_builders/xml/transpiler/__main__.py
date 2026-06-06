# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CLI entry point for the XSD codegen.

Usage::

    python -m genro_builders.xml.transpiler \\
        --xsd path/to/schema.xsd \\
        --dialect-name FatturaElettronica \\
        --output path/to/fattura_elettronica.py

The CLI is intentionally minimal: parse args, run backend, run
generator, write file. Anything more elaborate (multi-schema bundles,
diff modes, dry-run reports) belongs in a future helper, not here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .backend import XmlschemaBackend
from .generator import PythonGenerator


def main(argv: list[str] | None = None) -> int:
    """Parse args, run the XSD backend + generator, write the module."""
    parser = argparse.ArgumentParser(
        prog="python -m genro_builders.xml.transpiler",
        description="Generate a Python element mixin from an XSD schema.",
    )
    parser.add_argument(
        "--xsd",
        required=True,
        type=Path,
        help="Path to the XSD schema file.",
    )
    parser.add_argument(
        "--dialect-name",
        required=True,
        help=(
            "Base name of the generated dialect (e.g. FatturaElettronica). "
            "The module declares <name>Builder and <name>Handler."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file. If omitted, writes to stdout.",
    )
    parser.add_argument(
        "--module-docstring",
        default=None,
        help="Optional module-level docstring (overrides the default).",
    )
    args = parser.parse_args(argv)

    model = XmlschemaBackend().load(args.xsd)
    source = PythonGenerator().render(
        model,
        dialect_name=args.dialect_name,
        module_docstring=args.module_docstring,
    )

    if args.output is None:
        sys.stdout.write(source)
    else:
        args.output.write_text(source, encoding="utf-8")
        print(f"Wrote {args.output} ({source.count(chr(10))} lines)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
