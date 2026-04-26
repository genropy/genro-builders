# contrib/live — pending update

> **WARNING**: this contrib package is currently broken.

The live console (``cli.py``, ``_server.py``, ``_proxy.py``) accesses
``manager.global_store`` to expose the data Bag over the wire. That
property has been removed: the manager is now a registry of builders,
each owning a private ``local_store`` Bag.

Running this contrib will raise ``AttributeError`` on any data
operation. It is excluded from the active test suite.

## What needs to change

The CLI/server/proxy interface must be migrated from a single
``global_store`` view to a per-builder model:

- Replace ``manager.global_store[key]`` with
  ``manager.local_store(builder_name)[key]``.
- Decide whether the wire protocol exposes one builder at a time
  (current shape, scoped) or aggregates them into a per-builder
  namespace.
- Update the ``DataProxy`` / ``data`` command surface accordingly.

## Status

- Decision (2026-04-26): rework deferred to a dedicated tranche after
  the manager refactor stabilises.
- Reference: ``docs/builders/manager-architecture.md`` v0.2.0, §3 and §4.
