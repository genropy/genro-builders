# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Australia demo: states loaded from a CSV in ``setup()``, one row per state.

Shows the ``setup() -> main()`` lifecycle at work: ``setup()`` reads the
CSV and fills ``self.data`` *before* ``main()`` runs, so ``main()`` can
loop over the data it finds and build a repeated structure. Each row is
built by the ``@struct_method`` ``stateRow``, with a relative ``datapath``
so its inner pointers (``^.name``, ``^.capital``, ...) resolve against the
state's own subtree.
"""

from __future__ import annotations

import csv
from pathlib import Path

from genro_builders import struct_method

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "Australia"

_CSV_PATH = Path(__file__).parent.parent / "resources" / "australia.csv"


class Demo(InteractiveDemo):
    """The states of Australia, one panel per state, fed from a CSV.

    Data lives under ``states.<code>`` (``name``, ``capital``,
    ``description``); ``main()`` loops over the codes and emits a row each.
    """

    def setup(self):
        with _CSV_PATH.open(encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                code = row["code"]
                self.set_data(f"states.{code}.name", row["name"])
                self.set_data(f"states.{code}.capital", row["capital"])
                self.set_data(f"states.{code}.description", row["description"])

    def main(self, root):
        body = root.body(datapath="states")
        body.link(rel="stylesheet", href="demo_css")
        body.h1("States of Australia")
        # Bag iteration yields nodes, not keys; .keys() gives the codes.
        for code in self.data["states"].keys():
            body.stateRow(code)

    @struct_method
    def stateRow(self, pane, code):
        row = pane.section(datapath=f".{code}", _class="panel")
        row.h2("^.name")
        row.p("^.capital")
        row.p("^.description")


if __name__ == "__main__":
    demo = Demo()
    demo.create()
    print(demo.render())
