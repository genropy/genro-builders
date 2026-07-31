# ConfigBuilder + ConfigHandler

Configuration as a **distributed grammar**: the dialect declares only
the layout (`configuration` root, `server[0:1]`, the explicit
`applications` collection keyed by `code`); each application brings its
own vocabulary as the value of `app=` (subbuilder by reference). Every
path is stable and hand-writable: `configuration.server`,
`configuration.applications.<code>`.

The recipe produces the source; the runtime reads it ONLY through a
`ConfigHandler` — a callable with a four-layer stack: written value →
signature default (resolved at read time, the source stays pure) →
call-site `default=` → noisy `KeyError` with the full path.

## Install

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.builder import element
from genro_builders.contrib.config import ConfigBuilder, ConfigHandler


class ShopGrammar:
    @element(node_label="catalog")
    def catalog(self, title: str = "Untitled"): ...


class ShopApp:
    grammar = ShopGrammar


class InstanceConfig(ConfigBuilder):
    def main(self, root):
        c = root.configuration()
        c.server(host="localhost")
        c.applications().application(code="shop", app=ShopApp)


config = ConfigHandler(InstanceConfig)   # or a path to config.py, or an instance
config("server.host")                          # "localhost"  (written)
config("server.port")                          # 8000         (signature default)
config("applications.shop.catalog.title")      # "Untitled"   (mounted grammar's default)
config("server.workers", default=4)            # 4            (call-site default)
config("server.tls")                           # KeyError with the full path
```

An application never receives a subtree — it delegates with an explicit
prefix (two lines, no magic):

```python
class Application:
    def config(self, path, default=None):
        return self.server.config(f"applications.{self.code}.{path}", default=default)
```

## Parent recipes

A configuration can start from a base and update it — the legacy
`instanceconfig.xml`-over-defaults mechanism, rebuilt on executed
recipes:

```python
config = ConfigHandler(InstanceConfig, parents=[DefaultsConfig])
```

Each parent is a recipe in the same three forms as the source. Every
layer is executed, then the sources fold with `Bag.update` in
declaration order — first parent lowest, the main recipe last and
winning. Attributes merge per-name, explicit collections merge by key,
and a childless element in a higher layer inherits the lower subtree
instead of erasing it. Parents are recipes, never reloaded documents:
a dumped XML does not round-trip the grammar identity an executed tree
carries.

## Conventions

- Element parameters are **annotated** (`port: int = 8000`): only
  annotated parameters carry their default to the read stack, and types
  come back converted (`8000` is an `int`).
- An attribute that may come from outside (env, file, url) is annotated
  `str | BagResolver` and receives a resolver **in place** — no pointers
  in configuration grammars.
- A mounted grammar's top element declares `node_label=` so its path is
  hand-writable.
- A mount envelope's own arguments belong to the HOST grammar; only its
  children live in the mounted one.

Worked examples: `examples/01_instance_config/`,
`examples/02_parent_config/`. Design:
`roadmap/config-builder-design.md`.
