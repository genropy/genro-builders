# Creating Builder Packages

This guide covers the full picture: how the pieces fit together, when to use
each one, and how to structure a builder package for distribution.

For the individual pieces, see:
- [Custom Builders](custom-builders.md) — `@element`, `@abstract`, `@component`, `@data_element`
- [Custom Renderers](custom-renderers.md) — `BagRendererBase`, `BagCompilerBase`
- [Reactive Data](reactive-data.md) — `data_setter`, `data_formula`, `data_controller`

## The Chain: Builder → Manager → App

A builder package has three layers:

| Layer | Class | Role |
|-------|-------|------|
| **Builder** | `BagBuilderBase` subclass | Grammar machine — defines elements, materializes source → built |
| **Manager** | `BuilderManager` or `ReactiveManager` | Orchestrator — coordinates builders with shared data |
| **App** | User's subclass of the manager | Domain logic — populates data and source, produces output |

### Builder = Pure Machine

A builder is a **stateless grammar engine**. It knows:
- Which elements exist (`@element`, `@abstract`, `@component`)
- What children each element allows (`sub_tags`)
- How to validate parameters (`call_args_validations`)
- How to materialize source → built (the `build()` walk)

A builder does **not** know:
- Where data comes from
- What to render/compile
- When to subscribe to changes

```python
from genro_builders import BagBuilderBase
from genro_builders.builders import element, abstract, component

class RecipeBuilder(BagBuilderBase):
    @abstract(sub_tags="ingredient,step")
    def recipe(self): ...

    @element()
    def ingredient(self, qty: str = "", unit: str = ""): ...

    @element()
    def step(self): ...
```

### Manager = Orchestrator

The manager coordinates one or more builders around a shared data store.

**BuilderManager** — sync, one-shot pipeline:

```python
from genro_builders import BuilderManager

class RecipeManager(BuilderManager):
    def __init__(self):
        self.book = self.set_builder("book", RecipeBuilder)
        # Subclasses call self.run() to setup + build
```

**ReactiveManager** — adds `subscribe()` for live updates:

```python
from genro_builders import ReactiveManager

class LiveRecipeEditor(ReactiveManager):
    def __init__(self):
        self.book = self.set_builder("book", RecipeBuilder)
        self.run(subscribe=True)
```

### App = User's Domain Logic

The end user subclasses the manager and overrides `store()` and `main()`:

```python
class PastaRecipe(RecipeManager):
    def __init__(self):
        super().__init__()
        self.run()

    def store(self, data):
        data["title"] = "Carbonara"
        data["servings"] = 4

    def main(self, source):
        r = source.recipe(value="^title")
        r.ingredient("Spaghetti", qty="400", unit="g")
        r.ingredient("Guanciale", qty="200", unit="g")
        r.ingredient("Eggs", qty="4")
        r.step("Cook pasta al dente")
        r.step("Fry guanciale until crispy")
        r.step("Mix eggs with pecorino, combine")
```

### Downstream Reference

Existing packages that follow this pattern:

| Package | Builder | Manager | Output |
|---------|---------|---------|--------|
| genro-office | WordBuilder, ExcelBuilder | WordApp, ExcelApp | .docx, .xlsx |
| genro-print | ReportLabBuilder | PrintApp | PDF |
| genro-textual | TextualBuilder | TextualApp (ReactiveManager) | TUI widgets |
| genro-scriba | — | — | YAML (via YamlRendererBase) |


## build() vs render() vs compile()

These three operations form the output pipeline:

```
source Bag ──build()──> built Bag ──render()──> string/bytes
                                  ──compile()──> live objects
```

### build() — Materialization

Always the first step. Transforms the source Bag into a built Bag:
- Expands components into their concrete elements
- Processes data elements (data_setter, data_formula, data_controller)
- Keeps `^pointer` strings formal (unresolved)
- Two-pass walk: data elements first, then normal elements

### render() — Serialized Output

Produces "dead" output: strings, bytes, files. The built Bag is walked,
`^pointers` are resolved just-in-time via `evaluate_on_node(data)`, and
the renderer formats each node.

**Use when**: the output is text (HTML, Markdown, XML, SVG, YAML).

```python
from genro_builders import BagRendererBase
from genro_builders.renderer import RenderNode

class RecipeRenderer(BagRendererBase):
    def render_node(self, node, ctx, parent=None, **kwargs):
        tag = node.node_tag or node.label
        value = ctx["node_value"]
        if isinstance(node.get_value(static=True), Bag):
            return RenderNode(before=f"<{tag}>", after=f"</{tag}>",
                              value=value, indent="  ")
        return f"<{tag}>{value}</{tag}>" if value else f"<{tag}>"
```

### compile() — Live Objects

Produces "live" output: widget trees, workbook objects, PDF elements.
The compiler creates objects that depend on a runtime (openpyxl, ReportLab,
Textual, etc.).

**Use when**: the output is an object graph, not serialized text.

```python
from genro_builders import BagCompilerBase, compiler

class RecipeCompiler(BagCompilerBase):
    def compile_node(self, node, ctx, parent=None, **kwargs):
        tag = node.node_tag or node.label
        value = ctx["node_value"]
        children = ctx.get("children", [])
        # ... create live widget or object
```

The compiler is always **top-down**: the handler runs first and returns an
object, then children are compiled with that object as their parent.

### The Walk — Same Pattern for Both

Renderer and compiler use the **same top-down walk**:

```
for each node:
  1. _resolve_context(node)        → attrs resolved
  2. handler(self, node, ctx, parent)  → returns result
  3. recurse into children with result as parent
```

The handler runs first, returns a result, then children are processed
with that result as their parent. The difference is only what
"parent" means:

- **Compiler**: parent is a **live object** (widget, workbook, dict).
  Children attach to it via side effects.
- **Renderer**: parent is a **list of strings** (or a ``RenderNode``).
  Children append their rendered text to it.

For renderers, a ``RenderNode`` wraps collected child strings with
opening/closing markup (e.g. ``<div>...</div>``). Leaf handlers
return a plain ``str`` which is appended to parent directly.

### Decision Table

| Output type | Method | Base class |
|-------------|--------|------------|
| HTML, Markdown, SVG, XML, YAML | `render()` | `BagRendererBase` |
| PDF (ReportLab), DOCX (python-docx) | `compile()` | `BagCompilerBase` |
| TUI widgets (Textual), spreadsheets (openpyxl) | `compile()` | `BagCompilerBase` |
| Both text and objects | Both — register a renderer AND a compiler | Both bases |


## Anatomy of a Builder Package

Recommended directory structure:

```
genro-myformat/
├── src/genro_myformat/
│   ├── __init__.py          # Public API exports
│   ├── builder.py           # MyFormatBuilder(BagBuilderBase)
│   ├── renderer.py          # MyFormatRenderer(BagRendererBase) — if text output
│   ├── compiler.py          # MyFormatCompiler(BagCompilerBase) — if object output
│   ├── manager.py           # MyFormatManager(BuilderManager)
│   └── examples/
│       ├── __init__.py
│       ├── simple_example.py      # Standalone builder (grammar demo)
│       └── manager_example.py     # BuilderManager pattern (production use)
├── tests/
│   ├── test_builder.py
│   ├── test_renderer.py     # or test_compiler.py
│   └── test_manager.py
├── docs/
│   └── ...
├── pyproject.toml
├── LICENSE
└── README.md
```

### The Builder Module

Define the grammar with `@element` decorators. Register the renderer or
compiler so it activates automatically:

```python
# builder.py
from genro_builders import BagBuilderBase
from genro_builders.builders import element, abstract
from genro_builders.renderer import renderer  # or compiler

class MyFormatBuilder(BagBuilderBase):
    @abstract(sub_tags="section,paragraph")
    def document(self): ...

    @element(sub_tags="paragraph")
    def section(self, title: str = ""): ...

    @element()
    def paragraph(self): ...

    @renderer()
    def render_section(self, node, ctx, parent):
        title = ctx.get("title", "")
        return RenderNode(before=f"== {title} ==", after="", indent="")
```

### The Manager Module

Fix the builder class so users don't need to know it:

```python
# manager.py
from genro_builders import BuilderManager
from .builder import MyFormatBuilder

class MyFormatManager(BuilderManager):
    def __init__(self):
        self.doc = self.set_builder("doc", MyFormatBuilder)

    def render(self):
        return self.doc.render()
```

### Examples

Always include at least two examples:
1. **Standalone builder** — shows the grammar (quick demo)
2. **Manager pattern** — shows the production lifecycle


## Sync vs Async

### BuilderManager — Sync, One-Shot

No event loop needed. The pipeline runs once:

```python
class Report(MyFormatManager):
    def __init__(self):
        super().__init__()
        self.run()  # setup + build in one call

    def store(self, data): ...
    def main(self, source): ...

report = Report()
print(report.render())
```

Use for: reports, exports, file generation, CLI tools, batch processing.

### ReactiveManager — Async, Live

Requires an event loop. After `subscribe()`, data changes trigger
re-render/re-compile automatically:

```python
class LiveEditor(ReactiveManager):
    def __init__(self):
        self.doc = self.set_builder("doc", MyFormatBuilder)
        self.run(subscribe=True)

    def store(self, data):
        data["title"] = "Draft"

    def main(self, source):
        source.section(title="^title")
        source.paragraph(value="Content here")

editor = LiveEditor()
editor.reactive_store["title"] = "Final"  # triggers re-render
```

Use for: live dashboards, TUI applications, ASGI config, Jupyter notebooks.

### ReactiveManager as a Guest

ReactiveManager does **not** create an event loop — it uses an existing one.
The host environment provides the loop:

| Host | Where subscribe happens |
|------|------------------------|
| Textual | `on_mount()` → `run(subscribe=True)` |
| ASGI server | Application startup hook |
| Jupyter | Kernel's event loop (already running) |
| asyncio.run() | Explicit loop via `await smartawait(manager.run())` |

The manager is always a **guest** of the loop, never the owner.


## Future Directions

### Live Render

In async context, a renderer with a destination becomes "live":
the destination receives incremental updates as data changes.
This turns render from a one-shot operation into a continuous stream.

### Context Manager Lifecycle

```python
async with LiveEditor() as editor:
    # enter: subscribe()
    editor.reactive_store["title"] = "Update 1"
    editor.reactive_store["title"] = "Update 2"
    # exit: flush + unsubscribe
```

### Generic CLI/REPL

A contrib module providing a generic ReactiveManager host for
terminal-based interactive use, without requiring Textual.
