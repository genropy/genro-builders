# Builders documentation guide

**Last Updated**: 2026-05-30
**Status**: 🟡 APPROVATO PARZIALMENTE — header bumped to v0.5.0; contenuto da rileggere.
**Audience**: Contributors writing documentation for a specific
grammar (HTML, SVG, CSS, ...) under `docs/grammars/<name>.md`,
and contributors writing framework-wide documentation under
`docs/builders/`.

This document defines **what to document** and **how to write it**
for every grammar that ships with `genro-builders`. The aim is
that a user opening `docs/grammars/<name>.md` can learn the
grammar end-to-end without reading source code.

---

## 1. Two documentation slots

The project keeps documentation in two separate slots:

### 1.1 `docs/builders/` — framework-wide

Cross-grammar topics. Written by a dedicated contributor commissioned
by the coordinator when a framework-wide change happens or a
pattern emerges. Audience: a developer **using** the framework.

Typical contents:

- `documentation-guide.md` — this file.
- `overview.md` — what a builder is, the two-phase lifecycle,
  the handler/builder/renderer triad.
- `patterns.md` — cross-grammar idioms (e.g. the `._` chaining
  pattern, `node_by_id`, render target registration and dispatch).
- `decorators.md` — `@element`, `@abstract`, `@subbuilder`,
  `@data_element`. The framework decorators.

### 1.2 `docs/grammars/` — per-grammar

One file per grammar: `docs/grammars/html.md`,
`docs/grammars/svg.md`, `docs/grammars/css.md`, etc. **Written by
the contributor who implemented that grammar**, as a deliverable
of the subtask. Audience: a developer using **that grammar**.

The author of a grammar is the most qualified person to document
it: knowledge is fresh, edge cases are still in mind, the API has
just been shaped. Documentation written long after the fact is
documentation written badly.

---

## 2. Required sections for `docs/grammars/<name>.md`

Every grammar file follows the same structure. Sections are listed
in order; some may be short or empty depending on the grammar, but
they should all be present so that readers know where to look.

### 2.1 Frontmatter

```markdown
# <Name> grammar

**Last Updated**: YYYY-MM-DD
**Status**: 🔴 / 🟡 / 🟢 (see project conventions)
**Maintainer**: (the subtask name that produced this grammar)

One-line description of what this grammar is for.
```

### 2.2 Purpose

What the grammar produces and what it does **not** produce. One or
two paragraphs.

Example: "The HTML grammar produces HTML5 markup conforming to the
W3C void-tag rules. It does not produce templates for server-side
rendering frameworks — for that, see `<other doc>`."

### 2.3 Quick start

Minimal end-to-end example, 5–10 lines, runnable. The reader must
be able to copy, paste, and see output.

```python
from genro_builders.contrib.<name> import <Name>BuilderHandler

class Hello(<Name>BuilderHandler):
    def main(self, root):
        ...

h = Hello(); h.create()
print(h.render())
```

### 2.4 Elements

Tabular list of the grammar's elements. For each element:

| Element | Type | Sub-tags | Parent tags | Notes |
|---------|------|----------|-------------|-------|
| `body` | container | flow | `html` | … |
| `img`  | leaf      | —    | flow        | void |
| `svg`  | subbuilder| —    | flow        | switches grammar |

"Type" is one of: container (has children), leaf (no children),
subbuilder (switches grammar), data_element (transparent).

If the grammar has many elements (HTML has 112), this can be
abbreviated as a categorical list with the full schema referenced
via auto-generated docs.

### 2.5 Common patterns

Idiomatic use of the grammar. Show how typical user code looks.
Reference `docs/builders/patterns.md` for cross-grammar idioms
(e.g. `._` chaining) rather than re-explaining them here.

Examples:

- "When emitting many leaves in a row, use `._` to chain back to
  the parent: `svg.rect(...)._.rect(...)._.circle(...)`."
- "To select a specific element later, declare `node_id="x"` at
  creation."

### 2.6 Render

Describe the available render modes for this grammar (the
`render_<mode>` methods on the renderer), what kwargs they accept,
and how the output looks.

Example for HTML: `render_html(xml=True/False, pretty=True/False)`,
short table of the four combinations.

### 2.7 Compile (when applicable)

Describe the compile output (typed objects, widgets, etc.) when
the grammar's compiler is implemented. If the compiler is still a
stub, write a one-line "Compiler not implemented yet" with a
forward reference to the relevant subtask.

### 2.8 Validation rules

What does the grammar enforce at build time? Examples:

- "`<rect>` is rejected outside of `<svg>`."
- "`<title>` inside `<head>` accepts only text."

This section also lists **which errors the grammar can raise** and
what they mean, so the user reading a stack trace knows where to
look.

### 2.9 Worked examples

Two or three concrete examples, each in its own subsection. Each
example shows:

- The user code (5–20 lines).
- The output (rendered, formatted).
- A one-paragraph commentary on what is interesting.

Reuse the examples from
`src/genro_builders/contrib/<name>/examples/` when available
(prefer linking to existing notebooks over duplicating code).

### 2.10 Known limitations

Anything the grammar **does not yet do** but might in the future.
Each item is a one-liner. Helps users know what to expect and
contributors know where the open doors are.

### 2.11 References

Cross-links to:

- The subtask that produced or last updated this grammar.
- The relevant section of `architecture-contract.md` if any.
- Other grammars referenced (e.g. SVG cites the `@subbuilder` mechanism).

---

## 3. Style rules

These apply to both `docs/builders/` and `docs/grammars/`.

### 3.1 Language

- All documentation is **in English**.
- No mentions of LLM/AI/Claude anywhere (project policy).
- No future-tense aspirational claims about unreleased features.
  If something is not implemented, say "not yet implemented" with
  a forward reference.

### 3.2 Tone

- Direct. Short sentences.
- Show, don't tell: examples beat prose.
- Avoid superlatives ("powerful", "elegant", "robust"). State
  facts, not opinions.

### 3.3 Code blocks

- Always specify the language: ` ```python `, not just ` ``` `.
- Examples must be **runnable** (or clearly marked as
  pseudo-code).
- Keep examples short: 5–20 lines. For larger demos, link to a
  file in `src/genro_builders/contrib/<name>/examples/`.

### 3.4 Links

- Use relative paths: `[file.py](../../src/...)`.
- Link to specific lines when useful: `[file.py:42](../../src/...#L42)`.
- Reference sections of other docs by anchor when stable.

### 3.5 Tables

- Used for enumerations (elements, options, errors).
- Not used for narrative content.

### 3.6 Status markers

Follow the project convention:

- 🔴 DA REVISIONARE
- 🟡 APPROVATO PARZIALMENTE
- 🟢 APPROVATO

A new grammar doc starts at 🔴. The status moves up only after
explicit user approval. Partial approval ("approved except section
X") is acceptable as 🟡.

---

## 4. Workflow for a grammar contributor

When the subtask that implements a grammar closes:

1. Create `docs/grammars/<name>.md` from this guide's template.
2. Fill all required sections (§2.1 to §2.11).
3. Run the examples in the doc to make sure they work.
4. Save with status **🔴 DA REVISIONARE**.
5. Mention the new doc in the subtask's `finaldoc.md`.
6. Wait for coordinator review.

If a grammar already has a doc and the subtask is updating the
grammar (e.g. adding new elements), update the existing doc rather
than starting over. Keep the version frontmatter current.

---

## 5. Workflow for a framework-wide contributor

When the coordinator commissions a doc under `docs/builders/`:

1. Read the briefing carefully.
2. Read `architecture-contract.md` and `data-architecture.md`
   first.
3. Read the relevant grammar docs only if they intersect the
   topic (e.g. `patterns.md` references all grammars).
4. Write the doc with this guide's style rules.
5. Save with status **🔴 DA REVISIONARE**.

The framework-wide contributor does **not** dig into source code
unless strictly necessary. The pubblic of `docs/builders/` is the
framework **user**, not the framework **maintainer**.

---

## 6. What this guide does not cover

- The internal architecture documents (`architecture-contract.md`,
  `data-architecture.md`) follow a different style: they record
  decisions, not how-to. They are not in scope of this guide.
- API-reference documentation generated from docstrings is a
  separate concern. If at some point the project ships a Sphinx
  build, that is governed by its own setup, not by this guide.
- The `examples/` folders under `src/genro_builders/contrib/`
  follow the three-view convention (`.py` + `.ipynb` + output)
  managed by the `genro-builders-example` skill — that is
  orthogonal to this guide.

---

**End of guide. Open questions and improvements go through the
coordinator.**
