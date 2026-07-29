# Config grammar (configuration trees)

**Last Updated**: 2026-07-29
**Status**: 🟢 APPROVATO — allineato al contratto v0.9.0 (BLD.2, emendamento 2026-07-29). Shipped in 0.22.0.

Configuration as a **distributed grammar**: the dialect declares only
the layout, each application brings its own vocabulary to the tree.
Reading goes through a single door, the callable `ConfigHandler`.

## Purpose

A configuration file (YAML, TOML, ...) cannot express a grammar: it
does not know the admitted tags, the cardinalities, the types, nor the
classes that will consume the values. A `ConfigBuilder` recipe does —
the schema IS the code that consumes it, and validation happens at the
line where you write the value.

## Quick start

```python
from genro_builders.builder import element
from genro_builders.contrib.config import ConfigBuilder, ConfigHandler


class ShopGrammar:
    @element(node_label="catalog")
    def catalog(self, title: str = "Untitled"): ...


class ShopApp:
    grammar = ShopGrammar        # any class exposing `grammar` mounts


class InstanceConfig(ConfigBuilder):
    def main(self, root):
        c = root.configuration()
        c.server(host="localhost")
        c.applications().application(code="shop", app=ShopApp)


config = ConfigHandler(InstanceConfig)
config("server.host")                       # "localhost"  (written)
config("server.port")                       # 8000         (signature default)
config("applications.shop.catalog.title")   # "Untitled"   (mounted grammar's default)
config("server.workers", default=4)         # 4            (call-site default)
config("server.tls")                        # KeyError carrying the full path
```

## Elements

| Element | Type | Sub-tags | Notes |
|---------|------|----------|-------|
| `configuration` | container | `server[0:1],applications[0:1]` | The single root element, stable label `configuration`. |
| `server` | leaf | — | `host: str \| BagResolver = None`, `port: int = 8000`. At most one; label = tag. |
| `applications` | container | `application` | The explicit collection: children labelled by their `code`. |
| `application` | mount | (from `app=`) | `code: str` (required, the natural key), `app=` carries the grammar of the subtree (`_meta={"subbuilder": "app:grammar"}`, contract `BLD.2`). |

Every path is **stable and hand-writable**: `configuration.server`,
`configuration.applications.<code>`. A project extends the layout by
subclassing `ConfigBuilder` — plain inheritance, as everywhere in
builders.

## The read door: four layers

`ConfigHandler` is built from a path to `config.py` (module convention:
exactly ONE `ConfigBuilder` subclass defined in it), a builder class, or
a builder instance. It runs `create()` when needed and owns the tree
(`handler.builder`). Calling it resolves, in order:

1. **written value** — what the recipe wrote. A `BagResolver` stored
   where the value lives (env, file, url) resolves here, invisible to
   the caller. A written `None` counts as absent.
2. **signature default** — resolved AT READ TIME from the addressed
   element's annotated signature; types come back converted
   (`port` → `8000`, an `int`). The source stays pure: a dump shows
   only what the recipe wrote. The layer needs the node to exist — an
   unwritten node skips ahead (past a mount the grammar is a call-site
   value, so there is nothing static to consult).
3. **call-site `default=`** — its presence suppresses the error layer.
4. **noisy error** — `KeyError` carrying the full requested path and
   the source address.

Paths are **relative to the root element**: `config("server.host")`
reads `configuration.server?host`; the last dotted segment is the
attribute, a single-segment path addresses the root element itself.

## App-side delegation

An application never receives a subtree: it knows its own `code` and
bounces to its parent with an explicit prefix — two lines, no magic:

```python
class Application:
    def config(self, path, default=None):
        return self.server.config(f"applications.{self.code}.{path}", default=default)
```

## Authoring conventions

- **Annotate the parameters** (`port: int = 8000`): only annotated
  parameters carry their default to layer 2, and the annotation is
  what validates the recipe at build time.
- An attribute that may carry a resolver is annotated with the union
  (`host: str | BagResolver`) — the typed signature would reject the
  resolver otherwise. No `^pointer` in configuration grammars: the
  resolver lives where the value lives.
- A mounted grammar's top element declares `node_label=` (here
  `catalog`) so its path is hand-writable; `node_label` does not guard
  duplicates — a second `catalog()` silently replaces the first.
- A mount envelope's own arguments (`code`, and any kwarg a subclass
  adds) belong to the **host** grammar; only its children live in the
  mounted one. The dispatch is deterministic, never a fallback.

## Render

`render()` serves the `xml` mode inherited from `BuilderBase` — no
dialect renderer code. The dump is the honest source: signature
defaults do not appear, and the mount kwarg stays literal
(`app="<class ...>"`).

## Validation rules

- A second `server` raises (`[0:1]`); a duplicate `code` among
  applications raises; a missing `code` raises (required).
- Unknown attributes raise (closed signatures — a typo never becomes
  a field); wrong types raise (`port="8000"`).
- A wrong child inside a mount raises at the recipe line, exactly like
  any wrong tag.

## Worked examples

`01_instance_config/` under
[src/genro_builders/contrib/config/examples/](https://github.com/genropy/genro-builders/tree/main/src/genro_builders/contrib/config/examples/):
a server, two applications with different grammars, the four layers
printed one by one, the XML dump.

## Known limitations

- `PreferenceHandler` (the symmetric door over the preference store)
  is future work — see `roadmap/config-builder-design.md` §6.
- No `branch()` (a handler cut on a subtree): prefix delegation covers
  the need.
- The mount kwarg in the XML dump (`app="<class ...>"`) will be
  revisited with the round-trip work.

## References

- Source: `src/genro_builders/contrib/config/`.
- Handler: `src/genro_builders/contrib/config/handler.py`.
- Design record: `roadmap/config-builder-design.md` (v0.3.1).
- Contract: `roadmap/architecture-contract.md`, clause `BLD.2`.
