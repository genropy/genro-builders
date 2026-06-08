# 01 — Inline styling

CSS is passed as keyword arguments on any element, plus a few Genro
styling macros.

## CSS as kwargs

Style properties are plain kwargs; underscores become hyphens:

```python
body.div("hello", color="white", background="#3498db", padding_top=12)
```

- `color`, `background`, `padding` … → CSS properties.
- `padding_top`, `font_size`, `text_align` … → sub-properties
  (`padding-top`, `font-size`, `text-align`).
- `style="..."` can be mixed with kwargs; on collision the kwargs win.
- `style_<prop>` is the escape for properties outside the curated list
  (e.g. `style_aspect_ratio="3 / 1"` → `aspect-ratio: 3 / 1`).

## Genro macros

A handful of `<macro>_<sub>` kwargs expand to common CSS patterns:

- `rounded=12` / `rounded_top=20` → `border-radius` (all corners / top).
- `transform_rotate=-3`, `transform_scale=0.95` → a `transform`.
- `filter_blur=2`, `filter_contrast=80` → a `filter`.

## Output

See `output.html`.
