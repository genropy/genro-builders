# 14 — Page command

A button that must RUN SERVER LOGIC (add a row, remove a row) — and
why it is still an ordinary `{id, value}` mutation.

## The FIRE lane

The wire has one road: the client sends WHO (the element id) and at
most WHAT (a raw value). The first three lanes write a datum (a
`value` pointer typed by the node, a `checked` pointer, a
`set-pointer` whose value is declared on the node). The fourth lane
is the **page command**: the node declares

- `data-fire-pointer` — the path to FIRE (the topic);
- `data-fire-value` — optionally, the message.

The server resolves the node by identity and FIREs the path: the
write is an EVENT (`_fired`, never persisted) and the datastore acts
as a message bus. Path and payload semantics never come from the
client's hands: the path is always the node's own attribute.

## The hybrid payload rule

- node declares `data-fire-value` → that IS the message, the click is
  pure identity (the per-row "−" bakes its row label at expansion);
- no declaration → the client's `value` is the message (a widget can
  send a rich JSON payload on the same wire);
- neither → `True` (the footer "+" needs no payload).

Declaring both `data-set-pointer` and `data-fire-pointer` on one node
is an authoring error.

## The subscriber is a data_controller

`data_controller(func="del_row", label="^commands.del_row")` — the
canonical data-element machinery: the fired event triggers the
controller, the func performs the STRUCTURAL store op (`Bag.pop`, or
a SET of a whole new row bag). The iterate block re-renders because
the store changed; the grand totals follow their `^rows` binding.

## Deletion kills the anchored rules

A dead row's rule must never run: its destination write would
autocreate the row back (the resurrection bug). On a `del` event the
handler eagerly purges every rule whose ANCHOR sits at or under the
deleted path — eagerly, because waiting for the re-expansion would
leave stale rules live for the rest of the cascade (a shared binding,
e.g. the exchange rate, would resurrect the row through the back
door). The criterion is the anchor, not the trigger: a rule of
another row READING under the deleted subtree keeps recomputing.

Run it from this folder:

```bash
python page_command.py
```
