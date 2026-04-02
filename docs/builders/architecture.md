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

## build() Flow

```{mermaid}
flowchart TB
    A["store(data)"] --> B["main(source)"]
    B --> C["build()"]
    C --> D[Expand components]
    D --> E["Resolve ^pointers against data"]
    E --> F[Register subscriptions in BindingManager]
    F --> G["render() or compile()"]
    G --> H["builder.output"]
```

- **store(data)** / **main(source)** — called if overridden by subclass
- **build()** — materializes source into built Bag
- **render()** — produces serialized output via `BagRendererBase`
- **compile()** — produces live objects via `BagCompilerBase`
