# genro-builders — Contract

This document defines the public interface and rules of the builder system.
All code in this repository and all code that depends on it must follow
this contract.

**Status**: 🔴 DA REVISIONARE

---

## What Builders Are

A builder defines a **grammar** — the set of elements that can be used
to build a structured document or UI. The grammar is expressed as Python
methods decorated with `@element`, `@component`, `@abstract`, or
`@data_element`.

A builder is a **machine**: you feed it a description (source), it
produces a materialized structure (built), and from there renderers
or compilers produce output.

Builders exist because:

- The same grammar can produce different outputs (HTML, SVG, PDF,
  live widgets) by swapping the renderer/compiler
- The built Bag is a stable intermediate representation — data can
  change without rebuilding
- Validation happens at build time, not at output time

## Core Concepts

### Source and Built

The builder maintains two Bags:

- **source** — the recipe. The user populates it with elements,
  components, and data elements. This is "what you want to build"
- **built** — the materialized structure. Produced by `build()`.
  This is "what was built". Components are expanded, data elements
  are processed, but `^pointer` strings are kept verbatim

The source is written once. The built can be rendered many times
with different data.

### Data Store

The data store is a Bag that holds the values referenced by `^pointer`
strings. In a standalone builder it's `builder.data`. In a manager it's
the shared `reactive_store`.

Data flows one way: from the data store into the built, at render time.
The built never writes back to the data store (except data elements
during build).

### Pointers

A `^pointer` is a string that starts with `^` and references a path
in the data store:

| Syntax | Meaning |
|--------|---------|
| `^title` | Absolute — reads `data["title"]` |
| `^.name` | Relative — resolved from this node's `datapath` chain |
| `^.?color` | Relative + attribute — reads attribute `color` of the data node |
| `#address.street` | Symbolic — finds node with `node_id="address"`, resolves from there |

Pointers are **not resolved at build time**. They stay as strings in
the built Bag and are resolved **just-in-time** during render/compile
by the node's `evaluate_on_node(data)` method.

### Datapath

A `datapath` attribute on a node sets the data context for that node
and all its descendants. Datapaths are hierarchical — a node's effective
datapath is the concatenation of all `datapath` attributes up the
ancestor chain.

```python
source.div(datapath="user")
    .span(value="^.name")    # resolves to data["user.name"]
    .div(datapath=".address")
        .span(value="^.city") # resolves to data["user.address.city"]
```

## Manager

A `BuilderManager` coordinates one or more builders with a shared
data store. It provides:

- `store(data)` — populate the shared data store
- `main(source)` / `main_<name>(source)` — populate each builder's source
- `setup()` — calls `store()` then `main()` for each builder
- `build()` — builds all builders
- `subscribe()` — activates reactivity on all builders

The execution order is: `store()` → `main()` → `build()` → `subscribe()`.

`store()` runs before `main()` so that data is available when the source
is being populated.

## Grammar Decorators

### @element

Defines a simple element in the grammar. The method body must be empty (`...`).

```python
@element()
def span(self): ...

@element(sub_tags="li")       # can contain li children
def ul(self): ...

@element(sub_tags="")          # leaf — no children allowed
def input(self): ...

@element(parent_tags="ul,ol")  # can only be placed inside ul or ol
def li(self): ...
```

### @abstract

Defines a content category that can be inherited but not instantiated.
Used to group `sub_tags` shared by multiple elements.

```python
@abstract(sub_tags="span,em,strong")
def phrasing(self): ...

@element(inherits_from="@phrasing")  # inherits sub_tags
def p(self): ...
```

### @component

Defines a composite structure with code logic. The method body is
**required** — it receives a fresh `Component` bag and populates it.

```python
@component(sub_tags="")
def login_form(self, comp, **kwargs):
    comp.input(name="username")
    comp.input(name="password")
    comp.button("Login")
```

Components are expanded **lazily** — the body runs during `build()`,
not when the component is called in the source.

Components support:
- `sub_tags` — what children can be added after creation
- `based_on` — inherit from another component
- `slots` — named insertion points
- `iterate` — replicate per data child (see below)

### @data_element

Defines a data infrastructure element that acts on the data store
during build. Not materialized in the built Bag.

```python
@data_element()
def data_setter(self, path, value=None, **kwargs):
    return path, {"value": value, **kwargs}

@data_element()
def data_formula(self, path, func=None, **kwargs):
    return path, {"func": func, **kwargs}
```

Three data elements are built-in: `data_setter`, `data_formula`,
`data_controller`.

## Iterate

When a component is called with `iterate="^path"`, the builder
replicates it once per child of the data bag at that path.

```python
@component(sub_tags="")
def badge(self, comp, **kwargs):
    comp.text("^.?name")

def main(self, source):
    source.badge(iterate="^people")
```

The component describes **one instance**. The builder handles
replication. Each instance gets `datapath` set to the child's path,
so relative pointers (`^.?name`) resolve against the correct data node.

## The Node (BuilderBagNode)

Every node in the built Bag is a `BuilderBagNode`. The node is
responsible for resolving its own data. These are its public
resolution methods:

| Method | Purpose |
|--------|---------|
| `evaluate_on_node(data)` | Resolve all attrs + value (2-pass) |
| `current_from_datasource(value, data)` | Resolve a single value |
| `get_attribute_from_datasource(attr, data)` | Resolve one attribute |
| `abs_datapath(path)` | Resolve relative/symbolic path to absolute |

### Two-Pass Resolution (evaluate_on_node)

**Pass 1** — resolve non-callable attributes:
- `^pointer` strings → values from data store
- Plain values → returned as-is
- Callables → skipped

**Pass 2** — execute callables:
- Match parameter names against resolved attributes from pass 1
- If a parameter has a default that is a `^pointer`, resolve it from data
- If the callable accepts `**kwargs`, pass all non-private resolved attrs
- Call and use the result

```python
# Pass 1 resolves price and qty
# Pass 2 calls total with the resolved values
source.div(price="^item.price", qty=3,
           total=lambda price, qty: price * qty)
```

### Rule: resolution lives on the node

**No code outside `BuilderBagNode` may resolve `^pointer` values.**
Renderers, compilers, the build mixin — all must call node methods.
The node is the single point of resolution.

## Render vs Compile

Both transform the built Bag into output. The difference:

| | Renderer | Compiler |
|---|---------|----------|
| Output | Serialized (string, bytes) | Live objects (widgets, workbooks) |
| Base class | `BagRendererBase` | `BagCompilerBase` |
| Method | `render_node(node, ctx)` | `compile_node(node, ctx)` |
| Children in ctx | `str` (joined) | `list` (of objects) |
| Use case | HTML, SVG, Markdown, JSON | Textual TUI, openpyxl, DOM |

## Writing a Renderer

### What the base class does

`BagRendererBase` provides the complete pipeline:

```
render(built_bag)
  └─ _walk_render(bag)              # iterates nodes
       └─ _dispatch_render(node)    # for each node:
            ├─ _build_context(node) # calls evaluate_on_node → ctx
            │    └─ _walk_render(children)  # recurse
            └─ dispatch:
                 ├─ @renderer handler → handler(self, node, ctx)
                 └─ render_node(node, ctx)
```

The `ctx` dict contains:

| Key | Description |
|-----|-------------|
| `node_value` | Resolved value (string, empty if None) |
| `node_label` | Node's label |
| `children` | Already-rendered children (joined string) |
| `_node` | The BagNode (for structural info) |
| *(all attrs)* | Each resolved attribute as key-value |

### What you define

Override **only** `render_node`. Do **not** override `render()` with
your own walk.

```python
class MyRenderer(BagRendererBase):

    def render_node(self, node, ctx, template=None, **kwargs):
        tag = node.node_tag or node.label
        value = ctx["node_value"]
        children = ctx["children"]
        attrs = {k: v for k, v in ctx.items()
                 if not k.startswith("_")
                 and k not in CTX_KEYS}
        # produce output from tag, value, attrs, children
        ...
```

`CTX_KEYS` are the keys injected by the framework that are not real
attributes: `node_value`, `node_label`, `children`, `node`, `iterate`,
`datapath`.

If you need a different join strategy, override `render()` but
**keep using `_walk_render()`**:

```python
def render(self, built_bag, output=None):
    parts = list(self._walk_render(built_bag))
    return "\n\n".join(p for p in parts if p)
```

### Tag-specific handlers (@renderer)

For renderers where different tags need different formatting:

```python
# Declarative — template filled from ctx
@renderer(template="# {node_value}")
def h1(self): ...

# Imperative — full control
@renderer()
def table(self, node, ctx):
    return format_table(ctx)
```

When a `@renderer` handler exists for a tag, it takes priority over
`render_node`. Template-based handlers (empty body) call `render_node`
with the template as kwarg.

### What is forbidden

- Overriding `render()` with a custom recursive walk
- Reading `node.attr` or `node.get_value(static=True)` for output
- Calling `_resolve_pointer_from_data` or any build mixin method
- Duplicating resolution logic that `evaluate_on_node` already does

## Writing a Compiler

Same architecture, different output type:

```python
class MyCompiler(BagCompilerBase):

    def compile(self, built_bag, target=None):
        return list(self._walk_compile(built_bag))

    def compile_node(self, node, ctx, **kwargs):
        tag = node.node_tag or node.label
        value = ctx["node_value"]
        children = ctx["children"]  # list of objects
        # produce live object
        ...
```

Tag-specific handlers use `@compiler`:

```python
@compiler()
def button(self, node, ctx):
    return Button(label=ctx["node_value"])
```

## Provided Base Renderers/Compilers

### Base classes

| Class | Module | Output |
|-------|--------|--------|
| `BagRendererBase` | `genro_builders.renderer` | Abstract — subclass for string output |
| `BagCompilerBase` | `genro_builders.compiler` | Abstract — subclass for live objects |
| `YamlRendererBase` | `genro_builders.compilers` | YAML string (base for YAML-based configs) |

### Concrete renderers (in contrib/)

| Renderer | Builder | Module | Output |
|----------|---------|--------|--------|
| `SvgRenderer` | `SvgBuilder` | `genro_builders.contrib.svg` | SVG markup |
| `HtmlRenderer` | `HtmlBuilder` | `genro_builders.contrib.html` | HTML5 markup |
| `MarkdownRenderer` | `MarkdownBuilder` | `genro_builders.contrib.markdown` | Markdown text |

Each concrete renderer overrides only `render_node` and uses the base
class infrastructure for walk, resolution, and dispatch.

### YamlRendererBase

The YAML renderer has a 3-phase pipeline:

1. **Walk + resolve** — same as all renderers (evaluate_on_node)
2. **Produce dict** — merge duplicate keys (e.g. two nodes both
   producing `entryPoints:` are merged into one dict key)
3. **Serialize** — `yaml.dump(dict)` → string

The dict phase is an internal detail. The public interface is
`render() → str` like all other renderers.

Tag-specific handlers use `@renderer`, same as other renderers.
The `compile_TAG` dispatch on the builder is deprecated.

## Decorators Summary

| Decorator | Module | Purpose |
|-----------|--------|---------|
| `@element` | `genro_builders.builder` | Grammar element |
| `@abstract` | `genro_builders.builder` | Content category |
| `@component` | `genro_builders.builder` | Composite structure |
| `@data_element` | `genro_builders.builder` | Data infrastructure |
| `@renderer` | `genro_builders.renderer` | Tag-specific render handler |
| `@compiler` | `genro_builders.compiler` | Tag-specific compile handler |

## Public API (what `__init__` must export)

### Classes

- `BagBuilderBase` — builder base class
- `BagRendererBase` — renderer base class
- `BagCompilerBase` — compiler base class
- `BuilderManager` — multi-builder coordinator
- `BuilderBag` — Bag with builder support
- `BuilderBagNode` — node with resolution methods
- `Component` — typed bag for component handlers
- `BindingManager` — reactive subscription map

### Decorators

- `element`, `abstract`, `component`, `data_element` — grammar
- `renderer` — render handler
- `compiler` — compile handler

### Utilities

- `is_pointer(value)` — check if string is a `^pointer`
- `parse_pointer(raw)` — decompose pointer string
- `PointerInfo` — parsed pointer dataclass

### Contributed

- `YamlRendererBase` — YAML dict renderer

### Deprecated (to be removed)

- `render_handler` — use `renderer` instead
- `compile_handler` — use `compiler` instead
- `YamlCompilerBase` — alias of `YamlRendererBase`, use the renderer name
- `compile_TAG` dispatch on builder — use `@renderer` handlers

### Not exported (internal)

- `ComponentResolver`, `ComponentProxy` — internal machinery
- `SchemaBuilder` — available from `genro_builders.builder`
- `_dispatch_render`, `_dispatch_compile` — internal dispatch

## Lifecycle Summary

```
BuilderManager:
  __init__  →  set_builder("name", BuilderClass)
  setup()   →  store(data)  →  main(source)
  build()   →  pass 1: data elements  →  pass 2: materialize + expand
  subscribe()  →  activate reactivity (optional)
  render()  →  evaluate_on_node  →  render_node  →  output
```
