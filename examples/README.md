# Examples

Each example is a self-contained folder with a `.py` script and its
generated output file. Run the script to regenerate the output.

## Structure

```
examples/
├── sync/                          # BuilderManager (no event loop)
│   ├── html/
│   │   ├── simple_page/           # Standalone builder, minimal
│   │   ├── contact_list/          # BuilderManager with store/main
│   │   └── weather_dashboard/     # BuilderManager with API resolvers
│   ├── svg/
│   │   ├── bar_chart/             # Standalone, gradient bar chart
│   │   ├── concentric_circles/    # Standalone, target circles
│   │   ├── house_icon/            # Standalone, composed shapes
│   │   ├── card_shadow/           # Standalone, SVG filter
│   │   └── badge_sheet/           # BuilderManager + @component + iterate
│   └── custom_builder/
│       └── table_builder/         # Custom builder from scratch
└── reactive/                      # ReactiveManager (event loop)
    └── (coming soon)
```

Additional examples in contrib packages:

- `src/genro_builders/contrib/markdown/examples/sync/report/` — Markdown document
- `src/genro_builders/contrib/xsd/examples/` — SEPA XML payment (requires XSD file)

## Running

```bash
cd examples/sync/svg/bar_chart
python bar_chart.py
# generates bar_chart.svg in the same directory
```

## Patterns

- **Standalone builder** — direct builder usage, good for grammar demos
- **BuilderManager** — production pattern: `store()` + `main()` + `run()`
- **ReactiveManager** — live updates: adds `subscribe()` for reactive bindings
