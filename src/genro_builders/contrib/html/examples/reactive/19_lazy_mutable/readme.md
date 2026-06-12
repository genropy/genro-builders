# 19 — Lazy mutable

Laziness of the RENDER is orthogonal to the nature of the data.
Example 18 paged an immutable catalog (read_only resolver, parking,
silent transit, throwaway pages). Here the collection LIVES in the
store and stays fully editable — and paging gets SIMPLER.

## No parking, no transit

With a store-backed anchor there is nothing to park and nothing to
restore: a page renders by slicing the live collection at request
time. Always current by construction — an edit that lands between two
page requests is simply in the next page served.

## Everything editable already works

Rules are coordinate templates on the STORE, not artifacts of painted
blocks (CMP.7):

- the row formula of a never-painted row fires anyway (the dispatch is
  path arithmetic, not a DOM lookup);
- the grand total reads the whole collection from the first
  calculation — page 0 on screen, 250 rows in the sum;
- value edits ride the existing per-row/cell patch lanes — and the
  wire carries them ONLY for the rows the client HAS: the handler
  tracks the delivered pages (a container replace restarts the set),
  so a broadcast touching every row ships ~one page of ops, not N.
  The unpainted rows update in the STORE alone, which is already the
  truth; the page that eventually delivers them reads it fresh.

## The one new rule: structural ⇒ container replace

An insert or delete under a lazy anchor shifts the placeholder
arithmetic (page = index // page_size assumes a stable collection), so
per-row structural patches would lie. The flush answers with the
REPLACE of the enclosing container instead — and a lazy replace costs
page 0 plus a fresh marker count, not the world. The client rebuilds
its placeholders; the IntersectionObserver refills the viewport on its
own, wherever the scrollbar is.

## What the asserts pin

- first paint = page 0 + marker, store FULL, grand over all rows;
- page 2 served from the live store, store intact afterwards;
- value edit on a painted row: normal patches, container untouched;
- value edit on an unpainted row: its rule fires, the grand follows;
- add/del row: one container replace with the fresh count — never a
  row insert/remove, never a page op;
- a broadcast (the shared rate) updates the STORE for every row but
  ships value ops for exactly ONE page — the delivered one.

Contract: `roadmap/reactivity/lazy-iterate.md` (v0.4.0).
