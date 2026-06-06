# 07 — Structure validation

A builder's grammar is not just a list of tags: it constrains **where**
each tag may go, **how many** may appear, and **what arguments** they
accept. The schema enforces these at build time, so a malformed document
fails loudly instead of rendering wrong.

This example defines a tiny custom dialect — `recipe` — rather than
using HTML5 (whose `sub_tags` lists are huge and unreadable). The same
mechanisms apply to every dialect.

> Run it: `python 07_structure_validation.py` (prints XML + captured
> errors). It renders in `xml` mode — the focus is the grammar, not HTML.

## Defining the grammar

```python
class RecipeBuilder(BuilderBase):
    _name = "recipe"
    _default_render_mode = "xml"

    @abstract(sub_tags="*")
    def titled(self): ...

    @element(sub_tags="ingredient[1:],step[1:]", inherits_from="titled")
    def recipe(self): ...

    @element(parent_tags="recipe")
    def ingredient(self, node_value=None,
                   qty: Annotated[float, Range(gt=0)] | None = None): ...

    @element(parent_tags="recipe")
    def step(self, node_value: Annotated[str, Regex(r".+")] | None = None): ...
```

Four mechanisms are in play here.

## 1. `parent_tags` — where a tag may go

`ingredient` and `step` declare `parent_tags="recipe"`: they may only be
placed inside a `recipe`. Putting a `step` at the root raises:

```
ValueError: Element cannot be placed here: parent_tags requires one of
[recipe], but parent is 'root'
```

## 2. `sub_tags` cardinality — how many children

`recipe` declares `sub_tags="ingredient[1:],step[1:]"`. The `[min:max]`
suffix is the cardinality:

| Form | Meaning |
|---|---|
| `step[1]` | exactly one |
| `step[1:]` | one or more |
| `step[0:1]` | optional, at most one |
| `step` | wildcard count (no bound) |
| `*` (whole sub_tags) | any children |

A `[1:]` minimum is checked against the children actually present;
exceeding a maximum raises `Too many '<tag>'` at build time.

## 3. `@abstract` + `inherits_from` — shared rules

`@abstract` defines a reusable rule holder that is never instantiated.
`recipe` does `inherits_from="titled"`, pulling in the abstract's
`sub_tags="*"` contribution. Abstracts let several elements share a
containment policy without repeating it.

## 4. Call-argument validation — from the signature

An element's accepted arguments come from its **method signature**.
`Annotated` validators are read into the schema and enforced at call
time:

```python
qty: Annotated[float, Range(gt=0)] | None = None
```

Passing `qty=-5` raises:

```
ValueError: Validation failed: 'qty': must be > 0
```

`Regex(...)` works the same way for strings. The signature is the single
source of truth — no separate validation declaration.

## Takeaways

- `parent_tags` constrains placement; `sub_tags` with `[min:max]`
  constrains child counts.
- `@abstract` + `inherits_from` share containment rules across elements.
- Element call arguments and their validators come straight from the
  method signature (`Annotated[..., Regex/Range]`).
- All of it is enforced at build time, with explicit errors.
