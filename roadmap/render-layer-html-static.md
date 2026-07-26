# Layer 1 — static HTML render

**Version**: 0.1.0
**Last Updated**: 2026-07-26
**Status**: 🔴 DA REVISIONARE
**Parent**: [render-architecture.md](render-architecture.md)

> **Status after contract v0.9.0 (2026-07-26).** This layer is now **the
> whole Python core**, not merely the baseline of three: the handler is
> flat and static (`HND`), and updating means re-rendering (`RX.1`). Read
> it as current, with one correction — absolute data paths no longer carry
> a leading mount segment (`field`, not `page.field`).

The baseline layer: a source tree in, a document out. No client, no
reactivity, no identity. Everything the other two layers add sits on top
of this — and this layer must keep working when they are removed.

---

## 1. What it is

    builder.render(mode="html", target=...)  →  a string (or a written file)

One pass of the universal walk, `rendered_item` per node,
`finalize` joins and consumes the target. Nothing is retained: no
serials, no maps, no queue. Rendering twice produces the same document.

This is the only layer that needs no handler. A builder with pointers
still renders — `runtime_values` resolves them against whatever data is
reachable — but nothing subscribes and nothing recomputes.

## 2. What belongs here

- the walk (`RendererBase.render`, `render_children`, `preprocess`);
- per-node dispatch: `_handle_meta` (tag, `ns`, `render_attributes`),
  `adapt_attrs`, `rendered_item`;
- dialect boundaries via `get_render` — an `<svg>` subtree inside HTML
  is rendered by the SVG renderer throughout;
- component expansion (`_render_component`, `_expansion_inputs`,
  `_expand_block`) — expansion is a *static* fact: a component renders
  its body inline whether or not anything is reactive;
- minimum-cardinality validation, collected during the walk and raised
  by `render`;
- `finalize`: join for string dialects, target consumption
  (`None` → text, path → file, `.write` → file-like, callable → invoke);
- `TargetWrapper.full()` — a destination as an object, useful without
  any patch machinery.

## 3. What must NOT be here

No `target_id`. No `id` read off nodes. No patch vocabulary. The
contract already says it (`architecture-contract.md`): *the static
render carries no identity*.

Verify with a grep: in a clean core, `target_id` must not appear outside
the layer that needs it.

## 4. The one thing that is wrong today

**Row rules are gated by `include_datapath`.** A component body may
contain `dataFormula` / `dataController` — the row logic. They are
registered in `RendererBase._register_expansion_writeback`, which runs
only under `include_datapath`, i.e. only in reactive mode.

Consequence: a static render of a component with row logic **does not
register the rules at all**. That block (`set_component_rules` and the
`rule_nodes` collection) is general reactivity, not patch machinery, and
must be extracted into its own method called unconditionally from
`_expand_block`.

This is the only piece that moves *up* into the core when the layers are
separated; everything else moves down.

## 5. The gate

`include_datapath` is the switch between this layer and the reactive
one. It is a walk option, defaulted off, and set by the destination
(`TargetWrapper.render_opts`) rather than by the caller — the
destination dictates the form of the delivery.

Today it controls three distinct things at once:

| what | belongs to |
|---|---|
| emit `data-*-pointer` hooks next to bound attributes | reactive HTML |
| emit the element `id` (`_auto_id_attr`) | reactive HTML |
| register expansion writeback + row rules | mixed — rules are core (§4) |

When the layers separate, the first two stay behind the flag in the
reactive renderer; the third splits.

## 6. Rebuild check

If the reactive layers were deleted entirely, this layer must still:

- render every dialect in `contrib/` (html, svg, css, xslt, xsd);
- render the object dialects (genro-textual) — same walk, different
  `rendered_item` and `finalize`;
- pass every non-reactive example under `contrib/*/examples/`;
- register row rules in a component body (after the §4 fix).

---

## Riferimenti

Session-id: 6962ddd1-a3a9-4b94-8571-a279b59416a9.
