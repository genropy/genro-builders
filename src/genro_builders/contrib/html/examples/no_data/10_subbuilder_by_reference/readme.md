# 10 — Subbuilder by reference

`_meta['subbuilder']` has two forms. A plain name mounts a REGISTERED
dialect (`"svg"`, as in `03_subbuilders`). This example shows the second
form — a **parameter reference** `"kwarg:attr"`: the grammar governing
the subtree is not fixed in the host grammar, it comes from an object
the recipe passes at the call site.

## One declaration, grammar chosen by the recipe

```python
class AppsBuilder(BuilderBase):
    _default_render_mode = "xml"

    @element(sub_tags="application")
    def apps(self, **kwargs): ...

    @element(_meta={"subbuilder": "app:grammar"})
    def application(self, code=None, app=None): ...
```

`"app:grammar"` reads: *take the value the recipe passed as `app`, and
its `grammar` attribute is the grammar class for everything below this
node*. The recipe then mounts a grammar simply by passing the object
that carries it:

```python
app = root.apps().application(code="shop", app=ShopApp)
catalog = app.catalog(title="Summer sale")   # ShopGrammar's element
catalog.product(sku="S1", price=10)          # validated by ShopGrammar
```

`ShopApp.grammar` is a plain mixin of `@element` methods
(`Html5Elements` style) — no builder machinery: the core fabricates the
builder class once per grammar class and caches it; every node mounting
the same grammar shares one sub-builder instance per host, and the
host's datastore cascades across the boundary. Grammar specialization
is plain Python inheritance (`BankGrammar(ShopGrammar)`).

## The edges

- `app` left unset → **no switch**: the node stays a leaf of the host
  grammar (a child raises, `AppsBuilder` declares no `catalog`).
- object without the declared attribute, attribute not a class, class
  with no elements → noisy `ValueError` at the recipe line.
- a child the referenced grammar does not declare → raises at the
  recipe line, exactly like any wrong tag.
- the envelope keeps its attributes literal, so the mounting kwarg
  appears in the render as a string (`app="<class ...>"`).

## Why this example exists

This is the core primitive behind configuration-style dialects: an
element that says "from here down, the grammar is whatever the passed
object carries" — one declaration in the host grammar, the derivation
at the call site.

Run it from this folder:

```bash
python subbuilder_by_reference.py
```
