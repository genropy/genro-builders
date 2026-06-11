# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlContainersBase — fillable containers (the @container citizen).

The OTHER half of the collection (CMP.9): pieces that generate REAL
source nodes at call time, which the caller fills. Real nodes mean
real identity (``target_id``): every zone and pane is individually
patchable, and an <iframe> hosted inside survives the updates around
it (the client morph never disconnects matched elements).

- ``border_container`` / ``zone``: a CSS grid with named areas
  (top / left-center-right / bottom). Sizes live ON the zones; an
  absent zone collapses by itself (auto tracks) — zero arithmetic on
  the parent. ``zone("bottom", height="0")`` exists but collapsed,
  reopenable through data.
- ``tab_container`` / ``tab``: the selected key lives in DATA
  (``selected="^ui.tab"``), the click IS a mutation (the tab strip
  carries ``data-set-pointer``/``data-set-value``, the client
  translates the click into ``setData``). Visibility is pure CSS: a
  per-instance ``<style>`` accumulates one rule per key (keys are
  known at build time), keyed on the container's ``data-selected``
  attribute — which is a pointer, so switching tabs is an
  attribute-only morph: the panes are never touched, iframes inside
  never reload.

Usage::

    class Page(HtmlBuilder, HtmlContainersBase):
        def main(self, root):
            bc = root.border_container(height="100vh")
            bc.zone("top", height="48px").h1("Header")
            tc = bc.zone("center").tab_container(selected="^ui.tab")
            tc.tab("First", key="one").div("...")
            tc.tab("Second", key="two").iframe(src="widgets")
"""
from __future__ import annotations

from genro_builders.builder import container

_REGIONS = ("left", "right", "top", "bottom", "center")
_TAB_POSITIONS = {
    "top": "column", "bottom": "column-reverse",
    "left": "row", "right": "row-reverse",
}


class HtmlContainersBase:
    """Fillable layout containers. Mix into an HtmlBuilder."""

    #: per-instance progressive for unique tab-container tokens
    #: (class default; the first increment shadows it on the instance).
    _gnr_tabs_serial = 0

    # ------------------------------------------------------------------
    # border container — grid with named areas, sizes on the zones
    # ------------------------------------------------------------------

    # Explicit dispatch names: the legacy prefix-strip rule would turn
    # both compound names into "container" (a collision).
    @container("border_container")
    def border_container(self, pane, **attrs):
        return pane.div(
            class_="gnr-border-container",
            display="grid",
            grid_template_areas=(
                '"top top top" "left center right" "bottom bottom bottom"'
            ),
            grid_template_rows="auto 1fr auto",
            grid_template_columns="auto 1fr auto",
            **attrs,
        )

    @container
    def zone(self, pane, region, **attrs):
        if region not in _REGIONS:
            raise ValueError(
                f"unknown region {region!r}: one of {_REGIONS}",
            )
        return pane.div(
            class_="gnr-zone", grid_area=region,
            min_width="0", min_height="0", **attrs,
        )

    # ------------------------------------------------------------------
    # tab container — selected in data, click is a mutation, CSS shows
    # ------------------------------------------------------------------

    @container("tab_container")
    def tab_container(self, pane, selected=None, tabs_position="top",
                      **attrs):
        """The shell: tab strip + panes. ``selected`` is a reactive
        pointer to the selected key; ``tabs_position`` puts the strip
        on one of the four sides."""
        if selected is None:
            raise ValueError("tab_container() requires a selected pointer")
        if tabs_position not in _TAB_POSITIONS:
            raise ValueError(
                f"unknown tabs_position {tabs_position!r}: "
                f"one of {tuple(_TAB_POSITIONS)}",
            )
        self._gnr_tabs_serial = self._gnr_tabs_serial + 1
        token = f"gnr-tabs-{self._gnr_tabs_serial}"
        outer = pane.div(
            class_=f"gnr-tabs {token}", node_id=token,
            display="flex", flex_direction=_TAB_POSITIONS[tabs_position],
            **{"data-selected": selected}, **attrs,
        )
        # The per-instance rules: one base rule now, one per key as the
        # tabs are added (build time — the keys are the author's). A
        # <style> inside the container keeps it self-contained.
        outer.style(
            f".{token} > .gnr-tab-panes > .gnr-tab-pane "
            "{ display: none; }\n",
            node_id=f"{token}-style",
        )
        bar_direction = (
            "row" if tabs_position in ("top", "bottom") else "column"
        )
        outer.div(
            class_="gnr-tab-bar", node_id=f"{token}-bar",
            display="flex", flex_direction=bar_direction, gap="2px",
        )
        outer.div(
            class_="gnr-tab-panes", node_id=f"{token}-panes", flex="1",
        )
        return outer

    @container
    def tab(self, tabs, label, key=None, **attrs):
        """One tab: the strip gets the clickable label, the panes get
        the (returned) fillable pane, the instance style gets the
        per-key visibility and active-strip rules."""
        if key is None:
            raise ValueError("tab() requires a key")
        token = tabs.attr.get("node_id")
        selected_abs = tabs.abs_datapath(tabs.attr.get("data-selected"))
        bar = self.node_by_id(f"{token}-bar")
        panes = self.node_by_id(f"{token}-panes")
        styles = self.node_by_id(f"{token}-style")
        bar.div(label, class_="gnr-tab", **{
            "data-set-pointer": selected_abs, "data-set-value": key,
        })
        styles.set_value(
            styles.value
            + f'.{token}[data-selected="{key}"] > .gnr-tab-panes > '
              f'[data-key="{key}"] {{ display: block; }}\n'
            + f'.{token}[data-selected="{key}"] > .gnr-tab-bar > '
              f'[data-set-value="{key}"] '
              "{ background: #ffffff; border-color: #c8c8c8; "
              "font-weight: 600; }\n",
        )
        return panes.div(
            class_="gnr-tab-pane", **{"data-key": key}, **attrs,
        )
