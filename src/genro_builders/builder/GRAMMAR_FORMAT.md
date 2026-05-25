# `builder_grammar` v1.0 — format specification

**Last Updated**: 2026-05-19
**Status**: 🔴 DA REVISIONARE — documento non ancora approvato
**Format version**: 1.0

---

## 1. Purpose

The `builder_grammar` format is the **runtime contract** between a
Python builder (the producer, via `BagBuilderBase.to_grammar(path)`)
and any consumer that needs to reconstruct the same grammar in a
different environment:

- the upcoming **JavaScript builder**, which has no Python
  decorators and bootstraps its internal schema by reading a JSON
  document at startup time (the equivalent of Python's
  `__init_subclass__`);
- the future **`from_grammar` Python loader**, which reconstructs a
  builder class from an external document (e.g. a grammar authored
  by hand for a builder that lives natively in another language);
- any downstream transpiler (JSON Schema, XSD, RELAX NG) that needs
  a neutral starting point.

The format is therefore **language-neutral**: it must be readable
and reconstructible without any Python-specific machinery. It is
**not** an interchange format with foreign ecosystems: the
vocabulary (`element`, `abstract`, `subbuilder`, `sub_tags` /
`parent_tags` cardinality, `inherits_from`) is the vocabulary of
the Genro builder system. A consumer that does not understand
those concepts cannot use the document — and that is by design.

---

## 2. File extension and identification

| Aspect | Convention |
|---|---|
| File extension | `.json` (plain JSON). Recommended basename matches `grammar.name`, e.g. `html.json`, `svg.json`. |
| Identification by **content** | The very first key of the document is `document_format`, whose `name` field equals `"builder_grammar"`. |
| MIME type (internal) | `application/vnd.genro.builder-grammar+json` (Genro convention, not IANA-registered). |

Content-based identification is the canonical way for tools to
recognize a `builder_grammar` document. The file name is a
convention, not a contract.

---

## 3. Document structure

A `builder_grammar` document is a JSON object with **six top-level
keys**, always present, in this exact order:

```json
{
  "document_format": {"name": "builder_grammar", "version": "1.0"},
  "grammar": {
    "name": "html",
    "version": null,
    "title": null,
    "description": null
  },
  "abstracts":     { ... },
  "subbuilders":   { ... },
  "elements":      { ... },
  "data_elements": { ... }
}
```

### 3.1 `document_format`

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Always `"builder_grammar"`. Identifies the format. |
| `version` | string | Format version (e.g. `"1.0"`). Independent from `grammar.version`. |

`document_format` is **always the first key** of the document.

### 3.2 `grammar`

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Canonical name of the grammar (e.g. `"html"`, `"svg"`, `"css"`). Comes from `BagBuilderBase._name`. |
| `version` | string \| null | Version of this specific grammar (e.g. `"5.2.0"` for HTML5 revision 2). Optional. |
| `title` | string \| null | Human-readable title. Optional. |
| `description` | string \| null | Long-form description. Optional. |

Optional metadata fields are **present** in the document with
`null` value, not omitted. The document shape is stable.

### 3.3 Four sections, in usage order

| Section | Contents |
|---|---|
| `abstracts` | Abstract templates that define shared `sub_tags` / `parent_tags`. Consumed by `inherits_from`. Always emitted first because elements reference them. |
| `subbuilders` | Subbuilder entry points (a node that switches the active grammar to a different dialect). |
| `elements` | The instantiable, schema-validated elements of the grammar. |
| `data_elements` | Elements that bind data-infrastructure (tabular sections, etc.). |

Each section is a JSON object (not an array). Keys are element
names; values are the per-element form described in §4. **All four
sections are always present** even when empty (`{}`).

The sections are emitted in this order because a top-down reader
(e.g. the JavaScript bootstrap) wants to know the abstracts before
it processes the elements that inherit from them.

---

## 4. Per-element form

The shape of each per-element entry is fixed. All declared keys are
**always present**; missing values are explicit `null`.

### 4.1 Abstract

```json
{
  "doc": "Flow content (block-level).",
  "sub_tags": "p,div,section",
  "parent_tags": null,
  "inherits_from": null,
  "_meta": null
}
```

| Key | Type | Meaning |
|---|---|---|
| `doc` | string \| null | Documentation text (from the Python docstring of `@abstract`). |
| `sub_tags` | string \| null | Cardinality string for valid children. See §5. |
| `parent_tags` | string \| null | Cardinality string for valid parents. See §5. |
| `inherits_from` | string \| null | Comma-separated names of other abstracts (e.g. `"phrasing"` or `"phrasing,flow"`). **Literal, not resolved.** |
| `_meta` | object \| null | Pass-through metadata for renderers/compilers. No validation. |

### 4.2 Subbuilder

```json
{
  "doc": "Embed an HTML fragment.",
  "builder_name": "html",
  "parent_tags": null,
  "wrap_tag": "foreignObject",
  "wrap_attrs": {"xmlns": "http://www.w3.org/1999/xhtml"},
  "_meta": null
}
```

| Key | Type | Meaning |
|---|---|---|
| `doc` | string \| null | Documentation text. |
| `builder_name` | string | Canonical name of the grammar the subbuilder switches to (matches some other `grammar.name`). |
| `parent_tags` | string \| null | Cardinality string for valid parents. See §5. |
| `wrap_tag` | string \| null | Host-side wrap tag emitted at the boundary (declared by the host's `wrapper_<sub_name>` method). |
| `wrap_attrs` | object \| null | Framework attributes emitted on the wrap tag (e.g. XML namespace declarations declared by the host's `wrapper_<sub_name>` method). |
| `_meta` | object \| null | Pass-through metadata. |

### 4.3 Element

```json
{
  "doc": "Hyperlink.",
  "sub_tags": "a,abbr,b,em,strong",
  "parent_tags": null,
  "inherits_from": null,
  "attributes": null,
  "_meta": null
}
```

| Key | Type | Meaning |
|---|---|---|
| `doc` | string \| null | Documentation text. |
| `sub_tags` | string \| null | Cardinality string for valid children. See §5. |
| `parent_tags` | string \| null | Cardinality string for valid parents. See §5. |
| `inherits_from` | string \| null | Comma-separated names of abstracts to inherit from. **Literal, not resolved.** See §6. |
| `attributes` | object \| null | Reserved for the parametric-attribute plan (Step 3 of the broader subtask). **Always `null` in v1.0.** |
| `_meta` | object \| null | Pass-through metadata. |

### 4.4 Data element

```json
{
  "doc": "Bind a tabular section."
}
```

| Key | Type | Meaning |
|---|---|---|
| `doc` | string \| null | Documentation text. |

Data elements have the smallest shape; binding details are not part
of the neutral grammar contract.

---

## 5. `sub_tags` / `parent_tags` grammar

The `sub_tags` and `parent_tags` fields are **strings** that
declare child / parent constraints with cardinality. The format is:

```
<spec>      ::= <item> ("," <item>)*
<item>      ::= <name> <cardinality>?
<name>      ::= identifier   |  "*"
<cardinality> ::= "[" <min> ":" <max> "]"
                |  "[" <n> "]"
                |  "[]"
<min>       ::= integer | ""
<max>       ::= integer | "*" | ""
<n>         ::= integer
```

Semantics:

| Spec | Meaning |
|---|---|
| `""` (empty) | Leaf element. No children allowed. |
| `"*"` | Wildcard. Any children allowed, any number of times. |
| `"foo"` | Exactly one `foo` (default cardinality `[1:1]`). |
| `"foo[]"` | `foo` zero or more times (i.e. `[0:*]`). |
| `"foo[2]"` | Exactly two `foo`. |
| `"foo[2:5]"` | Two to five `foo`. |
| `"foo[1:*]"` | One or more `foo`. |
| `"foo,bar[]"` | Exactly one `foo`, plus zero or more `bar`. |

This is the same grammar used internally by `_parse_sub_tags_spec`
in `_grammar.py`. The spec is reproduced here so that the document
is self-contained: a consumer does not need to read Python source
to understand `sub_tags`.

---

## 6. `inherits_from` semantics

`inherits_from` is exported **literally**, as declared by the
grammar author. Examples:

```json
{"inherits_from": null}                  // no inheritance
{"inherits_from": "phrasing"}            // single parent
{"inherits_from": "phrasing,flow"}       // multiple parents
```

The document does **not** expand the inheritance: the inherited
`sub_tags` are not folded into the inheriting element. The
**consumer** is responsible for computing the transitive closure if
it needs it.

Rationale: consumers vary. A JavaScript builder may prefer the
closure to be pre-computed; a JSON Schema transpiler benefits from
the raw `inherits_from` (which becomes `allOf` in JSON Schema or
`xs:extension base` in XSD). Keeping the document literal pushes
the decision to the consumer.

**Invariant guaranteed by the exporter**: every name in
`inherits_from` resolves to an existing key in `abstracts`. The
exporter validates this at class-definition time in Python's
`__init_subclass__`. Consumers can therefore assume that
`inherits_from` references are never dangling. If a consumer
encounters a dangling reference, the document is malformed —
report it as a producer bug.

---

## 7. Section ordering and topological sort

### 7.1 Top-level sections

The six top-level keys appear in this exact order:

1. `document_format`
2. `grammar`
3. `abstracts`
4. `subbuilders`
5. `elements`
6. `data_elements`

Rationale: a top-down reader processes definitions before usages.
`abstracts` define contracts; `subbuilders` introduce alternate
grammars; `elements` reference both; `data_elements` describe
data-binding leaves.

### 7.2 Inside each section

Within each section, keys are emitted in **topological order**
relative to `inherits_from` dependencies, with insertion-order from
the source class schema as the secondary key.

For `abstracts`, this means an abstract like `flow` that declares
`inherits_from: 'phrasing'` appears **after** `phrasing` in the
section.

For `elements`, in practice today, elements inherit only from
abstracts (which live in a different section), so the topological
constraint inside `elements` collapses to insertion-order.

The guarantee is: **for any key K in a section, every name in
K's `inherits_from` either lives in another section that came
earlier (i.e. `abstracts`), or lives in the same section at an
earlier index**.

---

## 8. Versioning and evolution

Two independent versions live in the document:

- **`document_format.version`** — the version of **this format**.
  Bumped when the structure changes (additive in `v1.x`, breaking
  in `v2.0`). Consumers should check this before parsing.
- **`grammar.version`** — the version of the **specific grammar
  being described**. Bumped when the grammar itself evolves (e.g.
  HTML5.2 → HTML5.3). Independent from format version.

A producer is responsible for emitting `document_format.version`
that matches the format actually used. A consumer is responsible
for checking it and refusing documents with unsupported versions.

---

## 9. Known limitations of v1.0

- **Parametric attribute plan**: the `attributes` field on
  elements is always `null`. The format reserves the key but does
  not populate it. Element-level attribute constraints (`Range`,
  `Regex`, type annotations) will be introduced in v1.x.
- **No transpiler**: the format is the **source** of downstream
  transpilers (JSON Schema, XSD, RELAX NG) but does not include any
  of them. Transpilers are separate tools.
- **No CLI**: the exporter API is `Class.to_grammar(path)`. A
  command-line tool may be added later but is not required for v1.0.
- **`_meta` is opaque**: the format does not validate `_meta`
  contents. By convention, `_meta` values must be JSON-friendly
  (no callables, no class objects). A producer that includes
  non-JSON values will fail at serialization time with a standard
  `json.dumps` error.

---

## 10. References

- **Producer** (Python): `BagBuilderBase.to_grammar(path)` in
  [`base.py`](./base.py).
- **Implementation**: [`_grammar_export.py`](./_grammar_export.py).
- **Reference dialects**:
  [`contrib/html/`](../contrib/html/),
  [`contrib/svg/`](../contrib/svg/),
  [`contrib/css/`](../contrib/css/).
- **`sub_tags` parser** (Python reference):
  `_parse_sub_tags_spec` in [`_grammar.py`](./_grammar.py).

---

## Riferimenti

Documento prodotto nella sessione Claude Code locale del 2026-05-19
sul subtask `schema_export` (genro-builders).
