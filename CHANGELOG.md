# Changelog

## Unreleased

- Contract change: `${name}` templates expand only inside the attributes of
  non-data elements, the rule of genro-builders-js 0.3.0. The node value is not
  a template: `div("Ciao ${n}", n="^nome")` renders
  `<div n="Mario">Ciao ${n}</div>`. Data-element attributes (dataSetter,
  dataFormula, dataController) are never templates.
- `\${name}` stays the literal text `${name}`.
- A name that is not a resolved attribute raises
  `ValueError("Unknown template parameter 'name'")`, the message of JS.
- HTML: a string node value ending in `::HTML` is emitted as raw markup,
  without the suffix.
- Examples 07_address_block and 08_component_store compose ZIP and city with
  one span each.

## 0.25.0 — 2026-09-28

- A builder declares the SourceBag class of its Source in the class attribute
  `_source_class` (default `SourceBag`), as the legacy GenroPy page declares
  `domSrcFactory`. It is used for `_sourceroot`, `source`, `new_root()` and the
  component expansion root. genro-builders-js 0.3.0 uses `_sourceClass`.
- Branches created while authoring, including a promoted scalar node, follow
  the class of their parent bag; now covered by contract tests.
