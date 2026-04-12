# Creating Custom Renderers and Compilers

This guide explains how to create renderers and compilers for your builders.

## Key Concepts

A **renderer** transforms a built Bag into serialized output (string, bytes).
A **compiler** transforms a built Bag into live objects (widgets, workbooks).

Both share the same architecture:

1. **Walk** — the base class iterates over nodes in the built Bag
2. **Resolve** — for each node, `evaluate_on_node(data)` resolves all
   `^pointer` strings and callable attributes into concrete values
3. **Render/Compile** — the subclass defines how to format each node

You only need to define step 3. Steps 1 and 2 are handled by the base class.

## Architecture

```
render(built_bag)
  └─ _walk_render(bag, parent)         # iterates nodes (base class)
       └─ _dispatch_render(node, parent)  # for each node:
            ├─ _resolve_context(node)  # resolves ^pointers
            ├─ handler(self, node, ctx, parent)  # top-down
            └─ if RenderNode: recurse children, finalize
```

The `ctx` dict passed to your code contains:

| Key | Type | Description |
|-----|------|-------------|
| `node_value` | `str` | Resolved node value (empty string if None) |
| `node_label` | `str` | Node's label in the bag |
| `_node` | `BagNode` | The original node (for tag, structural info) |
| *all attributes* | `Any` | Each resolved attribute as a key-value pair |

Attributes starting with `_` are internal and should be filtered in output.
Infrastructure attributes like `iterate` and `datapath` should also be filtered.

### Handler Return Types

| Return | Meaning | Walk behavior |
|--------|---------|---------------|
| `RenderNode` | Container — children fill it | Recurse → finalize → append to parent |
| `str` | Leaf or fully handled | Append to parent, no recursion |
| `None` | Transparent | Children go into current parent |

## Creating a Renderer

### Minimal Example

The simplest renderer overrides only `render_node`:

```python
from genro_builders.renderer import BagRendererBase, RenderNode
from genro_bag import Bag

class PlainTextRenderer(BagRendererBase):
    """Render each node as 'tag: value' or 'tag:\\n  children'."""

    def render_node(self, node, ctx, parent=None, **kwargs):
        tag = node.node_tag or node.label
        value = ctx["node_value"]

        if isinstance(node.get_value(static=True), Bag):
            return RenderNode(before=f"{tag}:", indent="  ")
        if value:
            return f"{tag}: {value}"
        return tag
```

That's it. The base class handles:
- Walking the built Bag
- Resolving `^pointer` strings
- Resolving callable attributes (2-pass: pointers first, then callables)
- Recursing into children

### XML/Markup Renderer (SVG, HTML)

For markup output, `render_node` produces XML tags:

```python
from genro_bag import Bag
from genro_builders.renderer import BagRendererBase, RenderNode, CTX_KEYS

class XmlRenderer(BagRendererBase):

    def render_node(self, node, ctx, parent=None, **kwargs):
        tag = node.node_tag or node.label

        # Build attribute string from resolved ctx (skip internal keys)
        attrs = " ".join(
            f'{k}="{v}"'
            for k, v in ctx.items()
            if not k.startswith("_") and k not in CTX_KEYS
        )
        attrs_str = f" {attrs}" if attrs else ""
        value = ctx["node_value"]

        if isinstance(node.get_value(static=True), Bag):
            return RenderNode(
                before=f"<{tag}{attrs_str}>",
                after=f"</{tag}>",
                value=value,
                indent="  ",
            )

        if not value:
            return f"<{tag}{attrs_str} />"
        return f"<{tag}{attrs_str}>{value}</{tag}>"
```

### Using @renderer Handlers

For renderers where different tags need different formatting (like Markdown),
use the `@renderer` decorator:

```python
from genro_builders.renderer import BagRendererBase, renderer

class MarkdownRenderer(BagRendererBase):

    def render(self, built_bag, output=None):
        # Override only the join — use \n\n instead of \n
        parts = list(self._walk_render(built_bag))
        return "\n\n".join(p for p in parts if p)

    # Declarative: template-based
    @renderer(template="# {node_value}")
    def h1(self): ...

    @renderer(template="**{node_value}**")
    def bold(self): ...

    @renderer(template="[{node_value}]({href})")
    def link(self): ...

    # Imperative: custom logic
    @renderer()
    def blockquote(self, node, ctx):
        value = ctx["node_value"]
        return "\n".join(f"> {line}" for line in value.split("\n"))
```

Template-based handlers use `{key}` placeholders filled from `ctx`.
All attribute values are available as keys (already resolved).

### Dispatch Priority

When rendering a node with tag `T`:

1. If `@renderer` handler exists for `T` with logic body → call it
2. If `@renderer` handler exists for `T` with empty body → call `render_node` with decorator kwargs
3. No handler → call `render_node`

## Creating a Compiler

Compilers follow the same pattern but produce live objects instead of strings:

```python
from genro_builders.compiler import BagCompilerBase, compiler

class WidgetCompiler(BagCompilerBase):

    def compile(self, built_bag, target=None):
        return list(self._walk_compile(built_bag, parent=target))

    def compile_node(self, node, ctx, parent=None, **kwargs):
        tag = node.node_tag or node.label
        value = ctx["node_value"]
        children = ctx.get("children", [])
        # Create and return a widget object
        return create_widget(tag, value, children)

    # Or use @compiler for specific tags
    @compiler()
    def button(self, node, ctx, parent):
        return Button(label=ctx["node_value"])
```

## Registering with a Builder

```python
class MyBuilder(BagBuilderBase):
    @element()
    def item(self): ...

    # Register renderers and compilers
    _renderers = {"text": PlainTextRenderer}
    _compilers = {"widget": WidgetCompiler}
```

Usage:

```python
builder = MyBuilder()
builder.source.item("Hello")
builder.build()

# Render
output = builder.render()          # uses first renderer
output = builder.render("text")    # uses named renderer

# Compile
widgets = builder.compile("widget")
```

## Node Resolution Methods

The resolution infrastructure lives on `BuilderBagNode`. These methods
are available on every node in the built Bag:

| Method | Purpose |
|--------|---------|
| `evaluate_on_node(data)` | Resolve all attrs + value in 2 passes |
| `current_from_datasource(value, data)` | Resolve a single `^pointer` value |
| `get_attribute_from_datasource(attr, data)` | Resolve one attribute |
| `abs_datapath(path)` | Resolve relative/symbolic path to absolute |

### Two-Pass Resolution (evaluate_on_node)

Pass 1 resolves all non-callable attributes:
- `^pointer` strings → values from data store
- Plain values → returned as-is
- Callables → skipped (handled in pass 2)

Pass 2 executes callables:
- Inspects parameter names
- Matches them against resolved attributes from pass 1
- If a parameter has a default that is a `^pointer`, resolves it from data
- Calls the function with matched arguments

```python
# Example: callable attribute using other resolved attrs
source.div(
    price="^item.price",
    qty=3,
    total=lambda price, qty: price * qty,
)
# After evaluate_on_node:
# price=100, qty=3, total=300
```

## What NOT to Do

Do **not** override `render()` with a custom recursive walk.
This bypasses pointer resolution and breaks `^pointer` support.

```python
# WRONG — bypasses resolution
class BadRenderer(BagRendererBase):
    def render(self, built_bag, output=None):
        return self._my_walk(built_bag)

    def _my_walk(self, bag):
        for node in bag:
            # node.attr still has ^pointer strings!
            tag = node.node_tag
            value = node.get_value(static=True)  # NOT resolved
            ...
```

Instead, override `render_node` and let the base class handle the walk:

```python
# CORRECT — resolution handled by base class
class GoodRenderer(BagRendererBase):
    def render_node(self, node, ctx, template=None, **kwargs):
        # ctx has all values already resolved
        tag = node.node_tag or node.label
        value = ctx["node_value"]  # resolved
        ...
```

If you need a different join strategy, override only `render()` but
keep using `_walk_render()`:

```python
def render(self, built_bag, output=None):
    parts = list(self._walk_render(built_bag))
    return "\n\n".join(p for p in parts if p)  # custom join
```

## What's Next?

See [Creating Builder Packages](creating-builder-packages.md) for how to
structure a complete builder package with manager, examples, and tests.
