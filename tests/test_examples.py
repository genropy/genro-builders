# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Run every contrib example, and check its committed output is current.

Each example module under contrib/<dialect>/examples/ (except _old) is a
self-contained page on the new model; executing its __main__ exercises the
core through the real dialect. Running them all is the broadest coverage of
build/render/data/logic. A module that raises fails the test; output goes to
a throwaway cwd so no files leak into the repo.

The example folders also carry the rendered output as a committed file, so
the reader sees what a page produces without running it. That file is
documentation, and documentation goes stale: whatever an example writes into
the throwaway cwd is compared with the copy in the repo, so a renderer
change that alters the output fails here instead of leaving the folders
quietly wrong.
"""
from __future__ import annotations

import glob
import io
import os
import runpy
from contextlib import redirect_stdout

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Helper/non-example modules that live under examples/ but are not runnable
# example pages.
_SKIP = ("__init__.py", "__main__.py", "example_app.py")
_EXAMPLES = sorted(
    os.path.abspath(p)
    for p in glob.glob(
        os.path.join(_ROOT, "src/genro_builders/contrib/*/examples/**/*.py"),
        recursive=True,
    )
    if "_old" not in p
    and "__pycache__" not in p
    and os.path.basename(p) not in _SKIP
)


@pytest.mark.parametrize(
    "module_path", _EXAMPLES, ids=lambda p: os.path.relpath(p, _ROOT),
)
def test_example_runs(module_path, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with redirect_stdout(io.StringIO()):
        runpy.run_path(module_path, run_name="__main__")
    example_dir = os.path.dirname(module_path)
    for produced in sorted(tmp_path.iterdir()):
        committed = os.path.join(example_dir, produced.name)
        if not os.path.exists(committed):
            continue
        with open(committed, encoding="utf-8") as fp:
            expected = fp.read()
        assert produced.read_text(encoding="utf-8") == expected, (
            f"{produced.name} in {os.path.relpath(example_dir, _ROOT)} is "
            "stale: re-run the example and commit its output"
        )
