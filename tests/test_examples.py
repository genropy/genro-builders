# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Run every contrib example as a smoke test.

Each example module under contrib/<dialect>/examples/ (except _old) is a
self-contained page on the new model; executing its __main__ exercises the
core through the real dialect. Running them all is the broadest coverage of
build/render/data/logic/reactivity. A module that raises fails the test;
output goes to a throwaway cwd so no files leak into the repo.
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
