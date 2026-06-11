# 12 — Widget components

The first collection: `HtmlComponentsBase`, closed input widgets as
`@component`. Named after the WIDGET, not the HTML type (legacy
flavor):

| Widget | HTML underneath |
|---|---|
| `textbox` | `input type="text"` |
| `passwordbox` | `input type="password"` |
| `colorpicker` | `input type="color"` |
| `datepicker` | `input type="date"` |
| `timepicker` | `input type="time"` |
| `numberbox` | `input type="number"` |
| `slider` | `input type="range"` |
| `checkbox` | `input type="checkbox"` (state on `checked`) |

```python
class Page(HtmlBuilder, HtmlComponentsBase):
    def main(self, root):
        root.labeled_field(label="Born", kind="datepicker",
                           value="^.born", border=True, rounded=True)
```

## Reading AND writing

A reactive `value` pointer **passes through** to the inner `<input>`
(CMP.4): in the reactive render the element carries both the resolved
value and its write-back address —

```html
<input type="date" value="1980-05-12"
       data-value-pointer="main.person.born"/>
```

— so the widget displays, re-renders when the datum changes
(the component node is the registered reader, CMP.7), and the client
knows where to write when the user edits it. The checkbox rides
`checked` (`data-checked-pointer`, boolean by presence).

## labeled_field

Label + widget in one box (component-in-component, CMP.8): `kind`
names any widget of the collection, `label_position` is `top` (above,
left-aligned) or `left` (inline), `border`/`rounded` shape the box.
Styling is inline-minimal with class hooks (`gnr-field`,
`gnr-field-label`) for CSS overrides; the collection will carry its
own stylesheet when `cssrequires` (CMP.6) lands.

Extra attrs reach the inner input untouched (`min="0" max="120"`).

Fillable containers (border/tab/stack) are the OTHER citizen
(`@container`, CMP.9) and arrive separately.

Run it from this folder:

```bash
python widget_components.py
```
