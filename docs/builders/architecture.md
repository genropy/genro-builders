# Architecture

## Builder Structure

```{mermaid}
flowchart TB
    A["HtmlBuilder()"] --> B[source Bag]
    A --> C[compiled Bag]
    A --> D[data Bag]
    A --> E[BindingManager]
    A --> F[Compiler]
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

## compile() Flow

```{mermaid}
flowchart TB
    A["builder.compile()"] --> B[Expand components]
    B --> C["Resolve ^pointers against data"]
    C --> D[Register subscriptions in BindingManager]
    D --> E["Render compiled Bag to output"]
    E --> F["builder.output"]
```
