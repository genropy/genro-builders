# 06 — Render modes

The same document renders to several outputs. The mode is the first
argument to `render`; `pretty=True` indents the output.

```python
page = CustomPage()
page.create()
page.render(target=False)                  # html, compact (default mode)
page.render(target=False, pretty=True)     # html, indented
page.render("xml", target=False, pretty=True)  # xml view of the source
page.render("yaml", target=False)          # yaml view
```

- `target=False` means *return the string* — no file is written. Use it
  when you want the rendered text in hand (here, to print several modes
  side by side).
- An `HtmlBuilder` renders `html` by default; `xml` and `yaml` are
  always available as alternative views of the same source.

This example prints to the terminal, so there is no `output.html`.

## Output

Run the script to see the four renderings.
