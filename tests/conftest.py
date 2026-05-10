# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Force imports to resolve against this worktree's src/ tree.

A sibling worktree (``../genro-builders``) may be installed in the
active Python environment and would shadow our changes. Prepending
this worktree's src/ to sys.path before any test runs makes ``import
genro_builders`` resolve here.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
