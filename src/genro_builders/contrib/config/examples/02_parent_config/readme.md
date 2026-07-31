# 02 — Parent configuration

A recipe can start from a base and update it — the legacy GenroPy
mechanism where `instanceconfig.xml` overlays a defaults file, rebuilt
on executed recipes. `ConfigHandler` takes a `parents` list; each
parent is a recipe in the same three forms as the main source
(`config.py` path, builder class, builder instance):

```python
config = ConfigHandler(InstanceConfig, parents=[DefaultsConfig])
```

Every layer is **executed** (`create()`), then the sources are folded
with `Bag.update` in declaration order — first parent lowest, the main
recipe applied last and winning:

1. `server.host` → `"prod.example.com"` — written by both layers, the
   instance wins.
2. `server.port` → `9000` — written only by the base, inherited as-is
   (not the `8000` signature default).
3. `applications.shop.catalog.title` → `"Base catalog"` — a subtree the
   instance never mentions survives whole, signature defaults included.
4. `applications.crm.pipeline.stages` → `3` — an application added by
   the instance joins the collection next to the inherited one.

## Why executed recipes, not saved documents

A parent must be a recipe, never a reloaded `output.xml`: the dumped
XML does not round-trip the grammar identity (`node_tag`, `_meta`,
collection labels — `shop` would come back as `application_1`). An
executed tree carries all of it, so the merged result still renders
and still resolves signature defaults on every node.

## Inherit, never erase

A childless element in a higher layer (`configuration()` alone) has
value `None`: the fold uses `ignore_none=True`, so an empty section
inherits the lower subtree instead of wiping it. Attributes merge
per-name — rewrite what you name, keep the rest.

Run it from this folder:

```bash
python parent_config.py
```
