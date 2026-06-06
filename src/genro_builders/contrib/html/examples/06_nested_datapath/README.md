# 06 — Nested datapath

A `datapath` on a container sets the data scope for everything inside it.
Datapaths **nest**: a relative `datapath=".child"` composes onto the
scope of its ancestors. This is what lets one block of markup be reused
for many records — each instance just sits on a different sub-scope.

> Run it: `python 06_nested_datapath.py` (writes the `.html`).

Prerequisites: 05_pointers.

## A sub-bag per record

A `Bag` (here a `SourceBag`) built from a dict carries a whole record at
once. Seed one per record under a parent key:

```python
self.data.set_item("team.alice", SourceBag(
    {"id": "alice", "name": "Alice", "role": "Designer"},
))
```

Now `team.alice.name`, `team.alice.role`, ... all exist.

## Nesting the scope

The outer container opens `team`; an inner container narrows to one
record with a **relative** datapath:

```python
body = root.body(datapath="team")
card = body.div(datapath=".alice", class_="card")   # scope: team.alice
card.h3("^.name")                                    # team.alice.name
card.span("^.role")                                  # team.alice.role
```

The `.alice` is relative, so it composes onto `team` → `team.alice`. The
`^.name` pointers inside resolve against that narrowed scope — the card
markup knows nothing about *which* record it shows.

## Repeating the block

Because the block is scope-relative, repeating it is just a loop that
varies the datapath. Iterating the bag yields nodes; each node's `label`
is the record key:

```python
body = root.body(datapath="team")
for user in self.data["team"]:
    card = body.div(datapath=f".{user.label}", class_="card")
    card.h3("^.name")
    card.span("^.role")
```

Three users in, three cards out — same four lines of card markup, three
different sub-scopes. (A declarative form that removes the explicit loop
is on the roadmap; this is the explicit version.)

## Takeaways

- `datapath` sets a data scope; a relative `datapath=".x"` nests onto
  the ancestors' scope.
- A `Bag`/`SourceBag` from a dict seeds a whole record under one key.
- Pointers inside a nested scope are scope-relative, so the same markup
  serves any record.
- Iterating the data and varying the datapath repeats a block per
  record.
