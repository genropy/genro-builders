# 12 — Writeback identity

The virtual-children map (CMP.7), write-back side: how a mutation
coming from the client resolves entirely on the server.

## Derived identity

Expansion nodes never get a serial of their own — they reincarnate at
every render. In the REACTIVE render their identity is derived and
deterministic:

```
<base> . <iteration label> ... . <ordinal>
n1     . VIC                  . 4
```

- `base`: the component node's id (its serial, or the author's id —
  the author's id wins and seeds the chain);
- one label per store crossed (nested iterates chain naturally:
  `n1.SOUTH.4.TAS.2`);
- the ordinal follows the body's build order — the body is code, the
  rebuild is identical, so the id survives reincarnation.

The static render carries none of this.

## The map

While stamping ids, the renderer registers the WRITABLE nodes (a
pointer on `value` or `checked` — pure readers stay out) in
`builder._writeback_map`: derived id → expansion node. Re-expansion
purges its own prefix, so the map never holds stale rows.

## The mutation

The wire carries `{id, value}` and nothing else. The resolved node
says:

- **typing** — its `dtype` drives the TYTX conversion (text dtypes
  don't convert);
- **validation** — the `validate_*` family is retained on the node
  (never emitted in HTML: the renderer drops the retained families at
  emission) and will feed the validation engine;
- **destination** — its pointer, absolutized via `abs_datapath`.

No path and no dtype from the client: arbitrary-path writes and dtype
injection cease to exist as categories. Two widgets on the same path
stop being ambiguous — the id says WHICH widget the user edited
(legacy semantics: the editing widget's rules).

Run it from this folder:

```bash
python writeback_identity.py
```
