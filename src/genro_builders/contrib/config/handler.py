# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ConfigHandler — the callable read door of a configuration tree.

Built from one of three sources: a path to a ``config.py`` module
(the canonical instance form — the module defines exactly ONE
``ConfigBuilder`` subclass), a builder class, or a builder instance.
The handler runs ``create()`` when needed and owns the tree
(``handler.builder``).

``parents`` layers the tree over base recipes, the legacy
``instanceconfig.xml``-over-defaults mechanism: each parent (same three
forms as ``source``) is EXECUTED, then the sources are folded with
``Bag.update`` in declaration order — first parent lowest, the main
recipe applied last and winning. Parents are recipes, never
materialized documents: an executed tree carries the grammar identity
(``node_tag``, ``_meta``) a dumped XML cannot round-trip. The datastore
(``builder.data``) is not merged — configuration is static attributes.

``handler(path, default=...)`` resolves through four layers, in order:

1. **written value** — what the recipe wrote (``?attr`` on the source;
   a ``BagResolver`` stored as attribute value resolves here,
   transparent to the caller). A written ``None`` is indistinguishable
   from an absent attribute — the same "None = missing" semantics the
   signature validation applies at build time.
2. **signature default** — resolved AT READ TIME: from the addressed
   node up to its builder, reading the default declared in the
   element's ANNOTATED signature. The source stays pure — a dump shows
   only what the recipe wrote.
3. **call-site ``default=``** — its presence suppresses the error layer.
4. **noisy error** — ``KeyError`` carrying the full requested path.

Paths are RELATIVE to the root element: ``handler("server.host")``
reads ``configuration.server?host``. The last dotted segment is the
attribute name; a single-segment path addresses an attribute of the
root element itself. The documented application-side delegation
prefixes explicitly: ``self.server.config(f"applications.{self.code}.{path}")``.
"""

from __future__ import annotations

import importlib.util
import inspect
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ...builder import BuilderBase
from .config_builder import ConfigBuilder

_MISSING = object()


class ConfigHandler:
    """Callable read door over a configuration tree (four-layer stack)."""

    def __init__(
        self,
        source: str | Path | type | BuilderBase,
        parents: Sequence[str | Path | type | BuilderBase] | None = None,
    ):
        layers = [self._resolve_recipe(item) for item in (*(parents or ()), source)]
        builder = layers[0]
        for layer in layers[1:]:
            # ignore_none: a childless element in a higher layer has value
            # None — it inherits the lower subtree, it never erases it.
            builder.source.bag_update(layer.source, ignore_none=True)
        roots = list(builder.source)
        if len(roots) != 1:
            labels = [n.label for n in roots]
            raise ValueError(
                f"parent and main recipes must share one root element, "
                f"found {len(roots)}: {labels}",
            )
        self._builder = builder
        self._root_label = roots[0].label

    def _resolve_recipe(self, source: str | Path | type | BuilderBase) -> BuilderBase:
        """Resolve one layer to an EXECUTED builder with exactly one root.

        Accepts the three source forms (``config.py`` path, builder class,
        builder instance), runs ``create()`` when the tree is empty and
        enforces the exactly-one-root rule per recipe — a parent building
        zero or two roots is that recipe's error, reported before the fold.
        """
        if isinstance(source, (str, Path)):
            builder = self._load_recipe_class(source)()
        elif isinstance(source, type):
            if not issubclass(source, BuilderBase):
                raise TypeError(
                    f"ConfigHandler source class must be a BuilderBase "
                    f"subclass, got {source.__name__}",
                )
            builder = source()
        elif isinstance(source, BuilderBase):
            builder = source
        else:
            raise TypeError(
                "ConfigHandler source must be a config.py path, a builder "
                f"class or a builder instance, got {type(source).__name__}",
            )
        if not len(builder.source):
            builder.create()
        roots = list(builder.source)
        if len(roots) != 1:
            labels = [n.label for n in roots]
            raise ValueError(
                f"the recipe must build exactly one root element, "
                f"found {len(roots)}: {labels}",
            )
        return builder

    @property
    def builder(self) -> BuilderBase:
        """The builder instance whose tree this handler reads."""
        return self._builder

    @property
    def root_label(self) -> str:
        """Label of the single root element (paths are relative to it)."""
        return self._root_label

    def __call__(self, path: str, default: Any = _MISSING) -> Any:
        """Read ``path`` through the four-layer stack (see module docstring)."""
        node_path, attr = self._split_path(path)
        value = self.builder.source.get_item(f"{node_path}?{attr}")
        if value is not None:
            return value
        value = self._signature_default(node_path, attr)
        if value is not None:
            return value
        if default is not _MISSING:
            return default
        raise KeyError(
            f"missing config value '{path}' (source: '{node_path}?{attr}'): "
            "not written by the recipe, no signature default, "
            "no call-site default",
        )

    def _split_path(self, path: str) -> tuple[str, str]:
        """``'a.b.c'`` -> (``'<root>.a.b'``, ``'c'``); one segment -> the root itself."""
        if not path or not isinstance(path, str):
            raise ValueError(f"config path must be a non-empty string, got {path!r}")
        head, sep, attr = path.rpartition(".")
        if not sep:
            return self.root_label, path
        return f"{self.root_label}.{head}", attr

    def _signature_default(self, node_path: str, attr: str) -> Any:
        """Layer 2: the default declared in the addressed element's signature.

        Resolved from the NODE up to its builder: past a mount the grammar
        is a call-site value, so with no node there is nothing to consult —
        a missing node skips straight to layers 3/4. ``inspect.Parameter.empty``
        and a declared default of ``None`` both mean "no default" (the same
        "None = missing" semantics as the build-time required check).

        Dispatch is deterministic, never a fallback: a mount envelope's own
        arguments belong to the HOST grammar (only its children live in the
        mounted one), so a ``subbuilder``-marked node consults the host
        builder; every other node consults its own.
        """
        node = self.builder.source.get_node(node_path)
        if node is None:
            return None
        if node._get_meta("subbuilder"):
            builder = node.parent_bag._builder
        else:
            builder = node._resolve_builder()
        info = builder._get_schema_info(node.node_tag)
        entry = (info.get("call_args_validations") or {}).get(attr)
        if entry is None:
            return None
        default = entry[2]
        if default is inspect.Parameter.empty:
            return None
        return default

    def _load_recipe_class(self, path: str | Path) -> type:
        """Import ``config.py`` and return its single ``ConfigBuilder`` subclass.

        The module is executed from its file location and deliberately NOT
        registered in ``sys.modules`` (a recipe never shadows a real
        package, and must use absolute imports). Only subclasses DEFINED in
        the module count — an imported shared base recipe does not trip
        the exactly-one rule.
        """
        path = Path(path).resolve()
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot import config module from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        found = {
            obj
            for obj in vars(module).values()
            if isinstance(obj, type)
            and issubclass(obj, ConfigBuilder)
            and obj is not ConfigBuilder
            and obj.__module__ == module.__name__
        }
        if len(found) != 1:
            names = sorted(cls.__name__ for cls in found) or "none"
            raise ValueError(
                f"{path} must define exactly one ConfigBuilder subclass, "
                f"found: {names}",
            )
        return found.pop()
