# Examples — Core Framework

These examples demonstrate core genro-builders features that are not
specific to any contrib package. Each is a self-contained script.

## Structure

```
examples/
├── reactive_data_example.py   # ReactiveManager, data_formula, subscribe
└── table_builder/             # Custom builder from scratch with @element
```

## Contrib-specific examples

Domain-specific examples live inside their contrib package:

- `src/genro_builders/contrib/html/examples/` — HTML5 pages (standalone, BuilderManager, resolvers)
- `src/genro_builders/contrib/svg/examples/` — SVG graphics (charts, icons, filters, components)
- `src/genro_builders/contrib/markdown/examples/` — Markdown documents
- `src/genro_builders/contrib/xsd/examples/` — SEPA XML payments (XSD validation)

## Running

```bash
cd examples/table_builder
python table_builder.py
# generates table_builder.html
```

## Patterns

- **Standalone builder** — direct builder usage, good for grammar demos
- **BuilderManager** — production pattern: `store()` + `main()` + `run()`
- **ReactiveManager** — live updates: adds `subscribe()` for reactive bindings
