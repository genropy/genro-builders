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
```

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

| Decorator | Returns | Description |
|-----------|---------|-------------|
| `@element(sub_tags='child')` | Bag | Container, children allowed |
| `@element(sub_tags='')` | BagNode | Leaf, no children |
| `@element()` | BagNode | Leaf, no children |

## Lifecycle

```{mermaid}
flowchart TB
    A["setup()"] --> B["store(data)"]
    B --> C["main(source)"]
    C --> D["build()"]
    D --> E[Expand components]
    E --> F["Resolve ^pointers against data"]
    F --> G["subscribe() — optional"]
    G --> H[Register subscriptions in BindingManager]
    H --> I["render() or compile()"]
```

- **setup()** — on manager: calls `store(data)` then `main(source)` to populate
- **build()** — materializes source into built Bag (expand components, resolve pointers)
- **subscribe()** — optional: activates reactive bindings (data changes trigger re-render)
- **render()** — produces serialized output via `BagRendererBase`
- **compile()** — produces live objects via `BagCompilerBase`
