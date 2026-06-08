# 07 — Structure validation

A builder declares a grammar, and the grammar constrains the tree: which
tags may nest where, how many, and what their arguments must look like.
This example defines a toy `recipe` dialect and shows it rejecting bad
structure.

```python
class CustomPage(BuilderBase):
    _name = "recipe"

    @abstract(sub_tags="*")
    def titled(self): ...

    @element(sub_tags="ingredient[1:],step[1:]", inherits_from="titled")
    def recipe(self): ...

    @element(parent_tags="recipe")
    def ingredient(self, node_value=None, qty: Annotated[float, Range(gt=0)] = None): ...

    @element(parent_tags="recipe")
    def step(self, node_value: Annotated[str, Regex(r".+")] = None): ...
```

What the grammar enforces:

- **parent_tags** — `ingredient`/`step` may only sit inside `recipe`;
  a `step` at the top level raises.
- **sub_tags cardinality** — `recipe` requires at least one `ingredient`
  and one `step` (`[1:]`).
- **inherits_from / abstract** — `recipe` inherits the `titled` abstract.
- **call-argument validation** — `qty` must be `> 0` (`Range(gt=0)`),
  `step`'s text must match `.+`. A negative `qty` raises.

The valid recipe renders; the two bad cases raise `ValueError`/`TypeError`,
caught and printed.

## Output

The valid recipe is in `output.xml`; run the script to see the two
rejected cases.
