# `importer/` — Manual diff tool for HTML5 grammar

This directory holds a **manual-use utility** for comparing the
hand-written HTML5 grammar in `../html5_elements.py` against the
current W3C HTML5 schema.

> **This is not a codegen pipeline.** Nothing here runs in CI.
> Nothing here regenerates `html5_elements.py` automatically. The
> Python mixin is **hand-written and curated**, and stays that way.
>
> The tool here is for a human to run **occasionally** to spot
> changes in the W3C schema and decide, case by case, which ones
> to port into `html5_elements.py`.

## Inventory

- **`html5_schema_builder.py`** — downloads the W3C RELAX NG
  schema (RNC), converts it to a Bag, and prints/saves a snapshot.
  Run by hand, never by CI.

## Why it exists

The hand-written `html5_elements.py` is curated for the typical
GenroPy use case. It may legitimately diverge from the W3C schema:

- It may **omit** elements (e.g. `<rb>`, `<rtc>` — deprecated
  Ruby tags rarely used outside academic Japanese content).
- It may **rename** an element to avoid Python keyword conflicts
  (`<del>` is exposed as `del_` in Python).
- It may **lag** behind the W3C schema (e.g. when a new element
  like `<selectedcontent>` lands in HTML 2024 and we have not yet
  decided whether to expose it).

To decide what to keep aligned and what to leave alone, we need a
way to see "what does the W3C say today?" — that is what this
tool is for.

## Workflow

When you want to check for drift:

```bash
# Activate the project venv first.
mkdir -p /tmp/html5_check
cd /tmp/html5_check
python -m genro_builders.contrib.html.importer.html5_schema_builder \
    --url "https://github.com/validator/validator/tree/main/schema/html5" \
    -o html5_schema.bag.mp --json
```

This will:

1. Download all 26 RNC files from the W3C `validator/validator`
   repository (about 200 KB total).
2. Convert them to RNG using `rnc2rng` (must be installed:
   `pip install rnc2rng`).
3. Parse the RNG with `lxml` (must be installed: `pip install lxml`).
4. Build a flat Bag with one node per element, each carrying a
   `sub_tags` attribute (the comma-separated list of allowed
   children).
5. Save the Bag as `html5_schema.bag.mp` (MessagePack, binary) and
   `html5_schema.bag.json` (TYTX JSON, human-readable).

The output is **not versioned**. It lives in `/tmp` (or wherever
you ran the command) and is discarded after you have inspected it.

## Comparing the snapshot with the current mixin

A small Python snippet does the comparison:

```python
from genro_bag import Bag
import importlib

fresh = Bag().fill_from('/tmp/html5_check/html5_schema.bag.mp')
mixin = importlib.import_module(
    'genro_builders.contrib.html.html5_elements'
)
mixin_labels = {
    name for name in dir(mixin.Html5Elements)
    if not name.startswith('_')
}
fresh_labels = {n.label for n in fresh}

print('Only in fresh schema:', sorted(fresh_labels - mixin_labels))
print('Only in current mixin:', sorted(mixin_labels - fresh_labels))

for n in fresh:
    if n.label not in mixin_labels:
        continue
    f = set(n.get_attr('sub_tags').split(','))
    # The mixin's sub_tags are not directly accessible without an
    # instance; the easiest way to inspect them is to import
    # HtmlBuilder and walk `_class_schema`.
```

Reading the output, decide for each delta:

- **New element worth exposing**: hand-edit `html5_elements.py` to
  add a new `@element(sub_tags='...') def <name>(self): ...`.
- **New element not worth exposing**: leave the mixin alone.
- **`sub_tags` widening on an existing element**: hand-edit the
  affected `@element(...)` to widen the constraint.
- **`sub_tags` narrowing or rename**: investigate — the W3C may
  have removed a child, or may be reflecting a deprecation.

There is no automation. Every change is a human decision.

## Known historical baseline (2026-04)

The mixin `../html5_elements.py` was generated **once**, in April
2026, from a snapshot of the W3C RNC of that period. The original
codegen step that turned the Bag snapshot into Python source is no
longer in the repository (it was a one-shot script). All
subsequent edits to `html5_elements.py` are by hand.

If a wholesale regeneration is ever needed (e.g. because the W3C
HTML5 schema has materially diverged), the right approach is:

1. Run the tool here to get a fresh Bag snapshot.
2. Hand-write a one-shot Python script that walks the Bag and
   emits `@element(...)` definitions in the desired style.
3. Diff the generated output against the current mixin, port the
   Genro-specific extensions (Python keyword escapes, omitted
   elements, custom docstrings) back into the new version.
4. Replace `html5_elements.py` in a single, reviewed commit.

This has never been needed since April 2026 and may never be.

## Dependencies

- `rnc2rng` (Python package, must also expose the `rnc2rng` CLI in
  `PATH`). Install with `pip install rnc2rng`.
- `lxml` (Python package). Install with `pip install lxml`.

Both are optional dependencies of `genro-builders`: they are
required only when running this tool, not at runtime.
