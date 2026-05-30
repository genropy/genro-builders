# Claude Code Instructions - genro-builders

**Parent Document**: This project follows all policies from the central [meta-genro-modules CLAUDE.md](https://github.com/softwellsrl/meta-genro-modules/blob/main/CLAUDE.md)

## Project-Specific Context

### Current Status
- Development Status: Alpha
- Has Implementation: Yes

### Project Description
Builder system for genro-bag — domain-specific grammars, rendering,
runtime data binding via pointers.

Provides `BagBuilderBase` (grammar) and `BuilderHandler` (engine that
drives create/render on a single builder instance). Rendering lives
in `RendererBase` and dialect-specific subclasses, exposed on each
builder as `renderer_<mode>` properties. Concrete dialects under
`contrib/`: HTML (`HtmlBuilderHandler`), SVG (`SvgBuilderHandler`),
CSS (`CssBuilderHandler`), XSD (schema codegen).

Pull-based data binding is in (`^pointer` / `=pointer` / `${name}`
templates, `node.runtime_values`, `handler.pointer_map`). Push
reactivity is on the roadmap (`RX` area of the contract). The
authoritative document is `roadmap/architecture-contract.md` v0.5.0.

---

**All general policies are inherited from the parent document.**
