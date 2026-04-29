# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for user-supplied ``main_*`` and ``main_kwargs={...}`` at component
call time, plus the ``main_datapath`` concatenation under ``iterate``.

Covers contract §2bis.8 (call-time injection forms) and §8.3 (framework
behaviour during iterate)."""
from __future__ import annotations

import asyncio

from genro_builders.builder import BagBuilderBase, component, element

_received: list[dict] = []


class _Recorder(BagBuilderBase):
    """Builder that records the ``main_kwargs`` each handler call receives.

    Defines a ``container`` element (root with absolute datapath, used as
    ancestor anchor for iterate) and a ``card`` component whose body is a
    ``box`` element marked as the main widget.

    Records to a module-level list because BuilderBag may construct a
    fresh builder instance internally; a class-level recorder survives.
    """

    @element(sub_tags="*")
    def container(self): ...

    @element(sub_tags="")
    def box(self): ...

    @component(main_tag="box", sub_tags="")
    def card(self, comp, main_kwargs=None):
        _received.append(dict(main_kwargs or {}))
        comp.box(**(main_kwargs or {}))


def _maybe_run(result: object) -> None:
    if asyncio.iscoroutine(result):
        asyncio.run(result)


# ---------------------------------------------------------------------------
# Forms of call-time injection
# ---------------------------------------------------------------------------


class TestMainKwargsForms:
    """``main_*`` and ``main_kwargs={...}`` are equivalent and merge."""

    def setup_method(self) -> None:
        _received.clear()

    def test_main_prefix_kwargs_routed_to_handler(self):
        builder = _Recorder()
        builder.source.card(main_color="red", main_height="23px")
        _maybe_run(builder.build())

        assert _received == [{"color": "red", "height": "23px"}]

    def test_main_kwargs_dict_routed_to_handler(self):
        builder = _Recorder()
        builder.source.card(main_kwargs={"color": "red", "height": "23px"})
        _maybe_run(builder.build())

        assert _received == [{"color": "red", "height": "23px"}]

    def test_main_prefix_and_dict_merged(self):
        """Per contract §2bis.8: explicit ``main_kwargs`` wins on collision."""
        builder = _Recorder()
        builder.source.card(
            main_color="red",
            main_kwargs={"color": "blue", "height": "23px"},
        )
        _maybe_run(builder.build())

        assert _received == [{"color": "blue", "height": "23px"}]

    def test_non_main_kwargs_stay_on_source_node(self):
        """Non-prefixed kwargs become attributes of the source node, not
        main_kwargs."""
        builder = _Recorder()
        builder.source.card(title="Card 1", main_color="red")
        _maybe_run(builder.build())

        source_node = next(iter(builder.source))
        assert source_node.attr.get("title") == "Card 1"
        assert "color" not in source_node.attr
        assert _received == [{"color": "red"}]


# ---------------------------------------------------------------------------
# Iterate + user main_datapath concatenation
# ---------------------------------------------------------------------------


class TestIterateMainDatapath:
    """Iterate injects ``datapath``; user-supplied ``main_datapath`` is
    concatenated as ``<user>.<row>`` per contract §2bis.8 / §8.3."""

    def setup_method(self) -> None:
        _received.clear()

    def _seed(self, builder: _Recorder) -> None:
        builder.data["items.r0.name"] = "alpha"
        builder.data["items.r1.name"] = "beta"
        builder.data["items.r2.name"] = "gamma"

    def test_iterate_no_user_main_datapath(self):
        """Without user ``main_datapath``, framework injects ``.<row>``."""
        builder = _Recorder()
        self._seed(builder)
        root = builder.source.container(datapath="items")
        root.card(iterate="^.")
        _maybe_run(builder.build())

        datapaths = [m.get("datapath") for m in _received]
        assert datapaths == [".r0", ".r1", ".r2"]

    def test_iterate_concat_main_datapath(self):
        """User ``main_datapath='alfa'`` + iterate → ``alfa.<row>``."""
        builder = _Recorder()
        self._seed(builder)
        root = builder.source.container(datapath="items")
        root.card(iterate="^.", main_datapath="alfa", main_color="red")
        _maybe_run(builder.build())

        rows = [(m.get("datapath"), m.get("color")) for m in _received]
        assert rows == [
            ("alfa.r0", "red"),
            ("alfa.r1", "red"),
            ("alfa.r2", "red"),
        ]
