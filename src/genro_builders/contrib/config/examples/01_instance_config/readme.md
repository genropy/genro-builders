# 01 — Instance configuration

A configuration is a document whose grammar is **distributed in the
classes that consume it**. The host dialect declares only the layout:

```python
class ConfigBuilder(BuilderBase):
    @element(sub_tags="server[0:1],applications[0:1]", node_label="configuration")
    def configuration(self): ...

    @element(parent_tags="configuration")
    def server(self, host: str | BagResolver = None, port: int = 8000): ...

    @element(parent_tags="configuration", sub_tags="application", collection_key="code")
    def applications(self): ...

    @element(parent_tags="applications", _meta={"subbuilder": "app:grammar"})
    def application(self, code: str, app=None): ...
```

Each application brings its own vocabulary as the value of `app=`
(subbuilder by reference, see html example `10_subbuilder_by_reference`).
Every path is stable and hand-writable: `configuration.server`,
`configuration.applications.shop` — the sections label by their tag
(singleton cardinality), the collection members by their `code`.

## The read door: four layers

The recipe produces the source; the runtime reads it ONLY through a
`ConfigHandler`, callable, with paths relative to the root element:

1. **written value** — `config("server.host")` → `"localhost"`. A
   `BagResolver` stored where the value lives resolves here, invisible
   to the caller.
2. **signature default** — `config("server.port")` → `8000` (an `int`:
   types come from the annotated signature). Resolved AT READ TIME:
   the dump below shows no `port` — the source stays pure, only what
   the recipe wrote.
3. **call-site default** — `config("server.workers", default=4)` → `4`;
   its presence suppresses the error layer.
4. **noisy error** — `config("server.tls")` → `KeyError` carrying the
   full path and the source address.

Layer 2 also works **inside a mounted grammar**: `pipeline()` is written
with no attributes, yet `crm.config("pipeline.stages")` returns `3` from
`CrmGrammar`'s own signature.

## App-side delegation

An application does not receive a subtree: it knows its own `code` and
bounces to its parent with an explicit prefix — two lines, no magic:

```python
class Application:
    def config(self, path, default=None):
        return self.server.config(f"applications.{self.code}.{path}", default=default)
```

## Authoring conventions

- Attributes are **annotated** (`port: int = 8000`) — an unannotated
  parameter has no signature default at read time.
- An attribute that may carry a resolver is annotated with the union
  (`host: str | BagResolver`): typed signatures validate at build time.
- A mounted grammar's top element declares `node_label=` (here
  `catalog`, `pipeline`) so its path is hand-writable; note that
  `node_label` does not guard duplicates — a second `catalog()` would
  silently replace the first.
- The mount kwarg stays literal in the dump (`app="<class ...>"`): the
  envelope honestly shows what the recipe wrote.

Run it from this folder:

```bash
python instance_config.py
```
