# Claude Code Instructions - genro-builders

**Parent Document**: This project follows all policies from the central [meta-genro-modules CLAUDE.md](https://github.com/softwellsrl/meta-genro-modules/blob/main/CLAUDE.md)

## Project-Specific Context

### Current Status
- Development Status: Alpha
- Has Implementation: Yes

### Project Description
Builder system for genro-bag — grammar, validation, rendering, compilation, reactivity.

Provides `BagBuilderBase` (grammar machine), `BagRendererBase` (serialized output),
`BagCompilerBase` (live objects), `BuilderManager` / `ReactiveManager` (orchestration),
and concrete builders (HTML, Markdown, SVG, XSD) for creating structured Bag hierarchies
with domain-specific validation and reactive data binding.

---

**All general policies are inherited from the parent document.**
