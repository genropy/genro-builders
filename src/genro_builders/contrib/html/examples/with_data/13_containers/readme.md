# 13 — Containers

The OTHER citizen of the collection (`@container`, CMP.9): pieces that
generate REAL source nodes at call time, which the caller fills. Real
nodes mean real identity: every zone and pane is individually
patchable, and an `<iframe>` hosted inside survives the updates around
it.

## border_container / zone

```python
bc = body.border_container(height="360px")
bc.zone("top", height="48px").h2("Header")
bc.zone("left", width="160px").p("A sidebar")
bc.zone("center").tab_container(...)
bc.zone("bottom", height="0")     # exists but collapsed, reopenable
```

A CSS grid with named areas (`top / left-center-right / bottom`).
Sizes live ON the zones — the parent does no arithmetic: an absent
zone collapses by itself (auto tracks), a zero-sized one can be
reopened through data.

## tab_container / tab

```python
tc = bc.zone("center").tab_container(selected="^ui.tab",
                                     tabs_position="top")
tc.tab("People", key="people").p("Anna, Marco, Sara")
tc.tab("Places", key="places").p("Milano, Torino")
```

The selected key lives in DATA. Three cooperating pieces:

- the strip labels carry `data-set-pointer`/`data-set-value`: the
  client translates the click into `setData` — **the click is a
  mutation**, riding the same single road as the inputs;
- the shell carries `data-selected="^ui.tab"` (a reader): when the
  datum changes the patch is an **attribute-only morph** — the panes
  are never touched, iframes inside never reload;
- visibility is **pure CSS**: a per-instance `<style>` accumulates one
  rule per key (the keys are known at build time), keyed on the
  shell's `data-selected`.

`tabs_position` puts the strip on any of the four sides (`top`,
`bottom`, `left`, `right` — flex direction does the placement).

The live proof is the ws_live `desktop` page: tabs hosting OTHER live
pages in iframes; switching reloads nothing, the background clock
keeps ticking.

Run it from this folder:

```bash
python containers.py
```
