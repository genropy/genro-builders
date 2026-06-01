# genro-builders live demo

Interactive HTML builder REPL driven over WebSocket. A single-page app
served by `genro-asgi` hosts several demo pages (auto-discovered from
`pages/`); one is current at a time. Python snippets typed in the page's
editor run inside `page.live()` on the current demo. Every mutation
re-renders the document to `out.html`, and the browser reloads that file
in an iframe.

It doubles as a developer playground and as an end-to-end integration
check of `genro-builders` + `genro-asgi` + `genro-routes` + `WsxHandler`.

## Install

The demo lives behind the `live` extra:

```bash
pip install "genro-builders[live]"
```

The extra pulls `genro-asgi`, which brings `uvicorn` transitively — the
CLI delegates serving to `AsgiServer.run()`.

## Run

```bash
genro-live                       # localhost:8000
genro-live --port 9000 --open    # custom port, open the browser
```

Options: `--host`, `--port`, `--open`. The SPA is served at
`http://<host>:<port>/live/index`. Layout: a three-tab view on the left —
**Rendered** (the HTML in an iframe), **Raw** (the document as XML, the
structural source view), **Source** (the demo's Python); on the right a
demo selector, the SOURCE and DATA trees, a history pane, and the Python
editor.

The **Rendered** and **Raw** tabs are complementary: Rendered shows the
*result* (pointers resolved, framework metadata gone); Raw shows the
*source* (pointers like `^.title` left unresolved, `node_id` anchors still
on their nodes). A `node_id` is an internal anchor — it never reaches the
rendered markup, only the raw view.

## The REPL

You write **Python**, not a command language. Type a snippet in the
editor and press **Run** (or Ctrl/Cmd+Enter). The server runs it inside
`page.live()` on the **current demo**, so each mutation immediately
re-renders.

The namespace exposes a single name, **`page`** (the current
`InteractiveDemo`), and is **persistent across runs, per demo** — like a
real REPL, variables you define survive into the next run; switching demo
gives you that demo's own namespace.

`InteractiveDemo` adds two shortcuts on top of the handler:

```python
page.set_data("page.title", "Ciao")          # = page.data.set_item(...)
page.node["h1"].set_attr({"style": "color:red"})   # = page.node_by_id("h1")...
body = page.node["body"]                      # `body` survives next run
body.button("Click", _type="button")          # append a child
```

Notes:

- the data path separator is the **dot**: `page.title` means bag `page`,
  key `title` — not a comma;
- a snippet that raises is reported in the history pane; the page keeps
  running.

## Demos

The selector at the top of the right pane switches the current demo.
Shipped pages (in `pages/`):

| key | title | shows |
| --- | --- | --- |
| `australia` | Australia | states loaded from a CSV in `setup()`, one row per state via `@struct_method` |
| `basic` | Basic page | heading + paragraph bound to data |
| `dashboard` | Dashboard | header, nav, stat panels; `node_id` vs `node_label` |
| `signup` | Signup form | form with inputs, select, textarea |
| `styled` | Styled (inline CSS) | a self-contained page carrying its own `<style>` |
| `svg` | SVG shapes | vector graphics built inside the HTML page |

### Adding a demo

Drop a `pages/<key>.py` exposing a `Demo` class (subclass of
`InteractiveDemo`) and a `DEMO_TITLE`; it is **auto-discovered** — no
registry to edit:

```python
from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "My demo"

class Demo(InteractiveDemo):
    def setup(self):                      # optional initial data, runs before main
        self.set_data("x.title", "Hi")

    def main(self, root):
        body = root.body(datapath="x", node_id="body")
        body.h1("^.title", node_id="h1")
```

The file name (without `.py`) becomes the demo key. See
`pages/__init__.py` for how discovery works (dynamic import — a
documented, intentional bit of magic).

Name a node only when something looks it up later — naming is opt-in,
and the two ways differ:

- **`node_id`** — an absolute anchor, reached by `page.node_by_id("h1")`
  (this is what the REPL uses). The `basic` demo names `body` and `h1`
  for exactly that reason.
- **`node_label`** — a readable key in the source bag, reached by *path*
  via subscript at any depth: `source["body.panels.users"]` (segments may
  also be positional `#n`, mixed freely). The `dashboard` demo shows this.

Neither shows up in the rendered HTML. A node nothing reaches stays
anonymous — `signup` names nothing.

## Caveats

- **The REPL runs `exec` on code from the socket.** The builtins exposed
  to snippets are reduced for clarity, **not** as a security sandbox — a
  determined snippet can still break out. This is a local developer tool.
  **Do not expose it on a public interface.**
- **All demos live in parallel.** Every page is instantiated at startup
  and keeps its own state and namespace; selecting another only switches
  the pointer.
- **Full re-render per mutation** (RX level 0,
  `roadmap/reactivity/contract.md`) — fine for a demo, not an
  optimization target.
- **`out.html` and `out.xml` are generated** at runtime in `resources/`
  (the Rendered and Raw tabs read them) and are git-ignored.
- **No `<label>` tag** in the shipped demos: it collides with the
  `BagNode.label` property (tracked in issue #29). Other HTML5 tags work.
- **CodeMirror is optional.** The editor upgrades to CodeMirror when the
  CDN is reachable, and falls back to a plain textarea otherwise.
