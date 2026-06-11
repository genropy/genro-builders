# 04 — Methods

A page is a class, so repeated structure is just a method. Here `card`
is an ordinary Python method: it takes the parent node, builds a block
inside it, and `main` calls it several times.

```python
class CustomPage(HtmlBuilder):
    def card(self, parent, title, body, color="#3498db"):
        box = parent.div(class_="card", border_top=f"3px solid {color}")
        box.h3(title)
        box.p(body)
        return box

    def main(self, root):
        body = root.body()
        self.card(body, "Designer", "Alice", color="#e74c3c")
        self.card(body, "Engineer", "Bob", color="#2ecc71")
```

You call `self.card(parent, ...)` explicitly and pass the parent node in.
Nothing special — it is plain Python factoring.

The next example (`05_container`) shows `@container`, where the
block is invoked **from the node itself** (`body.card(...)`) instead of
through `self`.

## Output

See `output.html`.
