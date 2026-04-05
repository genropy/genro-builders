# Architecture

## Builder Structure

```{mermaid}
flowchart TB
    A["HtmlBuilder()"] --> B[source Bag]
    A --> C[built Bag]
    A --> D[data Bag]
    A --> E[BindingManager]
    A --> F["Renderers / Compilers"]
    A --> G[Schema: 112 HTML tags]
    A --> H[Formula Registry]
```

## Package Structure

`BagBuilderBase` is composed from four mixins, each responsible for a
distinct area:

| Module                 | Mixin              | Responsibility                                             |
| ---------------------- | ------------------ | ---------------------------------------------------------- |
| `_dispatch_mixin.py`   | `_DispatchMixin`   | `__getattr__`, element/component creation, validation      |
| `_build_mixin.py`      | `_BuildMixin`      | Build walk, pointer resolution, bindings, source changes   |
| `_reactivity_mixin.py` | `_ReactivityMixin` | Topological sort, formula re-execution, suspend/resume     |
| `_output_mixin.py`     | `_OutputMixin`     | render, compile, schema access, documentation              |
| `base.py`              | (main class)       | `__init__`, `__init_subclass__`, properties, data elements |

All mixins share the same `self` -- attributes are defined in `base.py.__init__`.

## Contributed Builders

Concrete builders live in `genro_builders.contrib/`, separate from the core:

| Builder            | Import                                            | Output   |
| ------------------ | ------------------------------------------------- | -------- |
| **HtmlBuilder**    | `from genro_builders.contrib.html import ...`     | HTML5    |
| **MarkdownBuilder**| `from genro_builders.contrib.markdown import ...` | Markdown |
| **XsdBuilder**     | `from genro_builders.contrib.xsd import ...`      | XML      |

The core package (`genro_builders.builder`, `genro_builders.builders`) provides
only the framework: `BagBuilderBase`, decorators, validators, `SchemaBuilder`.
Contributed builders depend on the core but are not loaded unless imported.

## Method Call Flow

```{mermaid}
flowchart TB
    A["builder.source.div()"] --> B{"'div' valid at this position?"}
    B -->|Yes| C["Create BagNode with tag='div'"]
    C --> D{Has children?}
    D -->|Yes| E[Return Bag]
    D -->|No| F[Return BagNode]
```

## Element Types

| Decorator                    | Returns | Description                       |
| ---------------------------- | ------- | --------------------------------- |
| `@element(sub_tags='child')` | Bag     | Container, children allowed       |
| `@element(sub_tags='')`      | BagNode | Leaf, no children                 |
| `@element()`                 | BagNode | Leaf, no children                 |
| `@data_element()`            | None    | Data infrastructure (transparent) |

## Lifecycle

```{mermaid}
flowchart TB
    A["setup()"] --> B["store(data)"]
    B --> C["main(source)"]
    C --> D["build()"]
    D --> E["Pass 1: data elements"]
    E --> F["Pass 2: normal elements"]
    F --> G["Topological sort formulas"]
    G --> H["Fire _onBuilt hooks"]
    H --> I["subscribe() -- optional"]
    I --> J["Register data subscriptions"]
    J --> K["Start _interval timers"]
    K --> L["render() or compile()"]
    L --> M["Just-in-time ^pointer resolution"]
```

- **setup()** -- on manager: calls `store(data)` then `main(source)` to populate
- **build()** -- two-pass materialization:
  - **Pass 1**: process data elements (`data_setter` writes, `data_formula` computes, `data_controller` executes)
  - **Pass 2**: materialize normal elements and components, register `^pointer` bindings in BindingManager
  - After passes: topological sort of formula dependencies, fire `_onBuilt` hooks
- **subscribe()** -- optional: activates reactive bindings. Enables:
  - Formula/controller re-execution on data changes (in topological order)
  - `_delay` debounce timers
  - `_interval` periodic timers
  - Source change handlers (incremental compile)
- **render()** -- produces serialized output via `BagRendererBase` with just-in-time `^pointer` resolution
- **compile()** -- produces live objects via `BagCompilerBase` with just-in-time `^pointer` resolution

## Pointer Formali

The built Bag retains `^pointer` strings verbatim. Resolution happens
just-in-time during render/compile via `_resolve_node()`:

```{mermaid}
flowchart LR
    A["built node: value='^title'"] --> B["_resolve_node()"]
    B --> C["data.get_item('title')"]
    C --> D["resolved: 'Hello'"]
    D --> E["renderer uses 'Hello'"]
```

This means:
- The built Bag is a **stable structural representation**.
- Multiple renderers can resolve the same built Bag with different data.
- Data changes don't require re-building -- only re-rendering.

## Formula Registry and Topological Sort

Data formulas with `^pointer` dependencies form a DAG (directed acyclic
graph). The builder sorts them topologically at build time:

```{mermaid}
flowchart LR
    A["data_setter 'base'"] --> B["data_formula 'doubled'"]
    B --> C["data_formula 'quadrupled'"]
```

- If formula A writes to path X and formula B reads `^X`, A executes first.
- Circular dependencies raise `ValueError` at build time.
- After `subscribe()`, when `^X` changes, dependent formulas cascade in order.

## 3-Level Propagation in BindingManager

When a data node changes, the BindingManager notifies affected built entries
with a `trigger_reason`:

| Level       | Meaning                                     |
| ----------- | ------------------------------------------- |
| `node`      | The exact data node that changed            |
| `container` | A parent Bag containing the changed node    |
| `child`     | A child path under the changed node         |
