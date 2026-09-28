# Changelog

## 0.25.0 — 2026-09-28

- A builder declares the SourceBag class of its Source in the class attribute
  `_source_class` (default `SourceBag`), as the legacy GenroPy page declares
  `domSrcFactory`. It is used for `_sourceroot`, `source`, `new_root()` and the
  component expansion root. genro-builders-js 0.3.0 uses `_sourceClass`.
- Branches created while authoring, including a promoted scalar node, follow
  the class of their parent bag; now covered by contract tests.
