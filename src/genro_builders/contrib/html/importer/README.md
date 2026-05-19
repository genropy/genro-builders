# `importer/` — Codegen artifacts for the HTML5 grammar

This directory holds the **build artifacts** of the pipeline that
generates the HTML5 grammar from external sources (W3C RELAX NG).
Nothing here is consumed at runtime by `HtmlBuilder`. The runtime
consumer is `../html5_elements.py`, which lives next to the builder.

## Inventory

| File | Role |
|---|---|
| `html5_schema.bag.json` | HTML5 schema in **TYTX/Bag JSON** format. Intermediate artifact: the parsed and structured version of the W3C RELAX NG schema. Input to the codegen step that produces `../html5_elements.py`. |
| `html5_schema.bag.mp` | Same content as `html5_schema.bag.json`, encoded in **MessagePack** (binary, smaller, faster to load). Twin of the JSON. |

## Expected pipeline

```
┌──────────────────────────────┐
│  W3C HTML5 RELAX NG schema   │   external (validator.nu / W3C)
│  (https://validator.nu/...)  │
└──────────────┬───────────────┘
               │  step 1: RELAX NG → structured Bag schema
               ▼
┌──────────────────────────────┐
│  html5_schema.bag.json       │
│  html5_schema.bag.mp         │   versioned in this directory
└──────────────┬───────────────┘
               │  step 2: codegen → Python mixin
               ▼
┌──────────────────────────────┐
│  ../html5_elements.py        │   class Html5Elements with 112
│  (read-only, generated)      │   `@element(sub_tags=...)` methods
└──────────────────────────────┘
```

`Html5Elements` is mixed into `HtmlBuilder` (see `../html_builder.py`)
so that `BagBuilderBase.__init_subclass__` picks up the 112 elements
at class definition time.

Custom Genro additions on top of the W3C grammar (e.g. the
`@subbuilder("svg")` entry point) live in `../html5_extensions.py`,
which is **NOT** generated and is preserved across regenerations
via the MRO order `HtmlBuilder(BagBuilderBase, Html5Extensions, Html5Elements)`.

## Current debt

> **The pipeline is not reproducible with the code currently in the
> repository.** The schema files in this directory are frozen
> artifacts produced by a previous, now-removed pipeline.

The historical converter modules — `html5_schema_builder.py`,
`rng_schema.py`, `rng_converter.py` — used to live in `genro-bag`'s
source tree but were removed during a past refactor. Their HTML
coverage reports survive in `genro-bag/htmlcov/`, but the source
files do not.

Two adjacent pipelines exist in the repository tree and may serve
as a starting point if a regeneration is needed, but neither is a
drop-in replacement for what produced the files in this directory:

- **`../../../../../scripts/rng_to_xsd.sh`** (in this repo, top level).
  Downloads the W3C RNG files and converts them to XSD via `trang`.
  Requires `brew install jing-trang`. Output: `temp/html5.xsd`.
  Different target format (XSD, not Bag).

- **`../../../../../../genro-treestore/scripts/build_html5_schema.py`**
  (in the `genro-treestore` repo). Downloads 26 RNC files from
  `github.com/validator/validator/tree/main/schema/html5`, parses them
  with `rnc2rng`, builds a **TreeStore** (not a Bag) and serializes
  to MessagePack/JSON TYTX. Different intermediate structure
  (TreeStore, not Bag).

If you need to regenerate the files in this directory, the most
practical path today is:

1. Reconstruct the equivalent of the deleted converter modules from
   the coverage reports in `genro-bag/htmlcov/` and the AST
   structure of `build_html5_schema.py`.
2. Validate the output against the existing `html5_schema.bag.json`
   (it should produce the same 112 elements and the same `sub_tags`).
3. Re-run the codegen step that produces `../html5_elements.py`
   (also currently un-versioned and missing).

This is non-trivial. If the W3C HTML5 schema has not changed in a
way that affects the 112 elements currently exposed, the safest
option is to keep the frozen artifacts as they are.

## Not to confuse with: `builder_grammar` export

A different JSON file may live one day next to `../html_builder.py`,
named `html.json`, produced by `HtmlBuilder.to_grammar('html.json')`
(see `src/genro_builders/builder/GRAMMAR_FORMAT.md`).

- `html5_schema.bag.json` (this directory) — **internal**: input to
  the codegen of `Html5Elements`. Format: Bag TYTX. Not consumed at
  runtime.
- `html.json` (sibling of `html_builder.py`) — **external**: output
  of `to_grammar`. Format: `builder_grammar v1.0` (neutral, cross-
  language). Consumed by the future JavaScript builder and by future
  `from_grammar` reconstruction in Python.

Same `.json` extension by coincidence; orthogonal purposes.

## When to touch this directory

- **Never** at runtime. Nothing under `importer/` is imported.
- **Only** when regenerating the HTML5 grammar from a newer W3C
  RELAX NG schema. Before doing so, read the **Current debt**
  section above and plan accordingly.
