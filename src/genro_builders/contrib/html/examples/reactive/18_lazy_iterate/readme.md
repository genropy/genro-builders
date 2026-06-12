# 18 — Lazy iterate

A 3000-row catalog must not make the first paint pay ~2.1 ms for every
row. Laziness lives in the DATA, the rendering follows the scroll.

## The author's two lines

The anchor declares WHERE the rows come from — a genro-bag resolver
with `read_only=True` (the result is never deposited on the node):

```python
data.set_item("catalog", BagCbResolver(self.load_catalog, read_only=True))
```

and the iterate opts in:

```python
body.catalog_row(iterate="^catalog", lazy=True, id="catalog_block")
```

Everything else is machinery.

## First paint: page 0 + the count

At first render the query runs ONCE. The rows go to the handler's
parking dict — keyed by the requesting node's id, split in pages of
100 — and the walk expands ONLY page 0 inline, plus a **marker**:

- `id="catalog_block.lazy"` — a mutation target (it sits in the wmap);
- `data-fire-pointer="_lazy.catalog_block"` — the lane to ask for more;
- `data-lazy-total` / `data-lazy-page` — the baked counts;
- the row blocks' own root tag (a div among the divs, a tr among the
  trs: DOM validity wherever the rows live), revealed by a build-only
  probe of the body.

The client draws the 100 real rows, measures their average height,
fabricates the missing placeholders with `min-height` = that average
(honest scrollbar from the start), and watches them with an
IntersectionObserver. No mount roundtrip: the first paint already
carries everything.

## Pages follow the scroll

An unfilled placeholder entering the viewport fires the marker with
the page number (`index // 100`) — the FIRE lane of example 14, the
client's value IS the message. The reply is one `page` op:

```python
{"id": "catalog_block", "op": "page", "page": 3, "html": "<50 blocks>"}
```

Grabbing the scrollbar and jumping works: page 3 never needs 1 and 2.

## Transit, not deposit

Block rendering resolves pointers (`^.name`) against the store, so a
page TRANSITS it silently — `set_item(anchor, page_bag,
resolver=False, do_trigger=False)`, render, restore the resolver the
same way. No events, no spurious row_ins; after delivery the anchor is
unresolved again. The DOM is the warehouse. Immutable data means no
rules, no writeback, no cell catalog — correctly so. Selection still
works: the per-row button bakes its label at expansion and stays in
the wmap (which retains expansion nodes, not store rows).

## What the asserts pin

- first paint = exactly page 0 blocks + marker with counts;
- the anchor stays unresolved (static read is None) before AND after
  any delivery;
- page 3 without pages 1-2, right rows, right values;
- an ordinary edit between two page requests rides its own
  transaction;
- firing a delivered row's button carries its baked label.

Contract: `roadmap/reactivity/lazy-iterate.md` (v0.3.0).
