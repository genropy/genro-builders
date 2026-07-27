# Claude Code Instructions - genro-builders

**Parent Document**: This project follows all policies from the central [meta-genro-modules CLAUDE.md](https://github.com/softwellsrl/meta-genro-modules/blob/main/CLAUDE.md)

## Project-Specific Context

### Current Status
- Development Status: Alpha
- Has Implementation: Yes

### Project Description
Builder system for genro-bag — domain-specific grammars, rendering,
runtime data binding via pointers.

Provides `BuilderBase` (grammar and document: it owns
`create()`/`render()`) and `BuilderHandler` (the data source: it mounts
ONE builder on one FLAT datastore and does not render). Rendering lives
in `RendererBase` and dialect-specific subclasses, exposed on each
builder as `renderer_<mode>` properties. Concrete dialects under
`contrib/`: HTML (`HtmlBuilder`), SVG (`SvgBuilder`), CSS (`CssBuilder`),
XSLT (`XsltBuilder`), XSD (schema codegen).

Pull-based data binding is in (`^pointer` / `=pointer` / `${name}`
templates, `node.runtime_values`, `handler.pointer_map`), together with
the data-elements at the first calculation and components
(`@component`/`@container`). The core is STATIC: a data change is
followed by rendering again — `live()`, the patch protocol and the
render queue were removed, and fine-grained reactivity is refounded on a
compiled bag emitted by a `livehtml` render mode (`RX` area of the
contract). The authoritative document is
`roadmap/architecture-contract.md` v0.9.0.

---

**All general policies are inherited from the parent document.**
