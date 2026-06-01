# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Australia demo: states loaded from a CSV in ``setup()``, one row per state.

Shows the ``setup() -> main()`` lifecycle at work: ``setup()`` reads the
CSV and fills ``self.data`` *before* ``main()`` runs, so ``main()`` can
loop over the data it finds and build a repeated structure. Each CSV row
is a dict, and a ``Bag`` built from a dict carries it whole — so one
``set_data`` per row loads a state's entire subtree at once. Each row is
built by the ``@struct_method`` ``stateRow``, with a relative ``datapath``
so its inner pointers (``^.name``, ``^.capital``, ...) resolve against the
state's own subtree.
"""

from __future__ import annotations

import csv
from pathlib import Path

from genro_builders import BuilderBag, struct_method

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "Australia"

_CSV_PATH = Path(__file__).parent.parent / "resources" / "australia.csv"


class Demo(InteractiveDemo):
    """The states of Australia in a table-grid, one row per state, from a CSV.

    Data lives under ``states.<code>`` (``code``, ``name``, ``capital``,
    ``description``); ``main()`` iterates the state nodes and emits a grid
    row each. Header and rows share the ``col-*`` classes so the columns
    line up (flex with fixed widths, in ``demo.css``).
    """

    def setup(self):
        # Each CSV row is a dict; a Bag built from it becomes one state's
        # subtree in a single set_data — its columns (name, capital, ...)
        # are the pointer targets the row reads with ``^.name`` etc.
        with _CSV_PATH.open(encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                self.set_data(f"states.{row['code']}", BuilderBag(row))

    def main(self, root):
        body = root.body(datapath="states")
        body.link(rel="stylesheet", href="demo_css")
        body.h1("States of Australia")
        grid = body.div(_class="grid")
        header = grid.div(_class="grid-row grid-head")
        header.span("Code", _class="col-code")
        header.span("Name", _class="col-name")
        header.span("Capital", _class="col-capital")
        header.span("Description", _class="col-desc")
        # Iterating the bag yields nodes; each node's value is the state's
        # own Bag, which stateRow reads through ``^`` pointers.
        for state in self.data["states"]:
            grid.stateRow(state.value)

    @struct_method
    def stateRow(self, pane, state):
        # ``code`` survives in the state data (no pop in setup), and here it
        # rebuilds the path back to this state under ``states``.
        code = state["code"]
        row = pane.div(datapath=f".{code}", _class="grid-row")
        row.span("^.code", _class="col-code")
        row.span("^.name", _class="col-name")
        row.span("^.capital", _class="col-capital")
        row.span("^.description", _class="col-desc")


if __name__ == "__main__":
    demo = Demo()
    demo.create()
    print(demo.render())
