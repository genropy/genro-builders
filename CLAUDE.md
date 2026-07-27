# Claude Code Instructions - genro-builders

**Parent Document**: This project follows all policies from the central [meta-genro-modules CLAUDE.md](https://github.com/softwellsrl/meta-genro-modules/blob/main/CLAUDE.md)

## Project-Specific Context

### Current Status
- Development Status: Alpha
- Has Implementation: Yes

### Project Description
Builder system for genro-bag — domain-specific grammars, rendering,
runtime data binding via pointers.

Provides `BuilderBase`: grammar, document AND datastore. It owns
`create()`/`render()` and one FLAT Bag, `builder.data`, reachable from
any node as `node.data`. Rendering lives in `RendererBase` and
dialect-specific subclasses, exposed on each builder as
`renderer_<mode>` properties. Concrete dialects under `contrib/`: HTML
(`HtmlBuilder`), SVG (`SvgBuilder`), CSS (`CssBuilder`), XSLT
(`XsltBuilder`), XSD (schema codegen).

The API is `page = P(); page.create(); page.render()`. `create()` runs
`setup` then `main` and computes the data-elements in document order;
`render()` is pure, and splits into `materialize` (the walk, whose
result survives in `materialized[mode]`) plus `finalize`. Rendering does
NOT validate: `validate_source()` reports on demand.

Pull-based data binding is in (`^pointer` / `=pointer` / `${name}`
templates, `builder.runtime_values(node)`), together with the
data-elements at the first calculation and components
(`@component`/`@container`). The core is STATIC: a data change is
followed by rendering again — `live()`, the patch protocol and the
render queue were removed. Fine-grained reactivity is a **separate
engine**, still under design (`RX.5`): the grammar is shared, but the
static engine EXECUTES the data-elements while the reactive one carries
them. The authoritative document is
`roadmap/architecture-contract.md` v0.9.0.

---

**All general policies are inherited from the parent document.**
