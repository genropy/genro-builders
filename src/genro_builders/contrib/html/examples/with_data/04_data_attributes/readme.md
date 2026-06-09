# 04 — Data attributes

A datum is not only a value: it can carry **attributes** too. A node can
read both — the value with `^path`, an attribute with `^path?attr`.

## A datum with attributes

`setup` seeds a datum that has a value **and** attributes:

```python
class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("name", "John", color="red", background="yellow")
```

`set_item` takes the value (`"John"`) and the extra keywords (`color`,
`background`) as attributes of the datum `name`.

## Reading value and attributes

The value is read with `^name`; an attribute of the datum with `^name?attr`:

```python
    def main(self, root):
        root.body().div(
            "^name", color="^name?color", background="^name?background",
        )
```

- `^name` → the div's text (`John`);
- `^name?color` → the datum's `color` attribute (`red`);
- `^name?background` → the datum's `background` attribute (`yellow`).

At render time each pointer is resolved against the data and replaced by its
value.

## Output

See `output.html`.
