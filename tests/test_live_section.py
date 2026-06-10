# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""live() — the handler's mutation critical section.

Whoever mutates the document does it inside ``with handler.live():``
(or via the ``@live`` method decorator): entering acquires the
handler's RLock, sections from other threads queue up, same-thread
nesting merges into the outermost section, the flush at the outermost
exit renders once toward the section target (or the registered
default). Outside a section nothing is queued; ``live()`` before
``activate()`` raises.
"""
from __future__ import annotations

import threading

import pytest

from genro_builders.builder import BuilderHandler, live
from genro_builders.contrib.html import HtmlBuilder


class _Page(HtmlBuilder):
    def main(self, root) -> None:
        body = root.body()
        body.data_setter("counter", 0)
        body.div("^counter", node_id="d1")


def _mounted(renders: list, application: bool = True):
    page = _Page(name="page")
    handler = BuilderHandler(application=object() if application else None)
    page.set_render_target(renders.append)
    handler.add_builder(page)
    handler.activate()
    renders.clear()              # discard the activate() first render
    return handler, page


def test_live_before_activate_raises():
    page = _Page(name="page")
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    with pytest.raises(RuntimeError, match="activate"):
        with handler.live():
            pass


def test_live_without_application_raises():
    renders: list = []
    handler, page = _mounted(renders, application=False)
    with pytest.raises(RuntimeError, match="application"):
        with handler.live():
            pass


def test_flush_renders_once_with_the_whole_batch():
    renders: list = []
    handler, page = _mounted(renders)
    with handler.live():
        handler.data["page.counter"] = 1
        handler.data["page.counter"] = 2
        assert renders == []          # nothing rendered mid-section
    assert len(renders) == 1
    assert ">2<" in renders[0]


def test_nested_section_merges_into_the_outermost():
    renders: list = []
    handler, page = _mounted(renders)
    with handler.live():
        handler.data["page.counter"] = 1
        with handler.live():          # same thread: re-enters and merges
            handler.data["page.counter"] = 2
        assert renders == []          # inner exit did NOT flush
    assert len(renders) == 1
    assert ">2<" in renders[0]


def test_nested_section_cannot_set_a_target():
    renders: list = []
    handler, _page = _mounted(renders)
    with handler.live():
        with pytest.raises(ValueError, match="nested"):
            with handler.live(target="elsewhere.html"):
                pass


def test_section_target_wins_for_that_section_only(tmp_path):
    renders: list = []
    handler, page = _mounted(renders)
    section_out = tmp_path / "section.html"
    with handler.live(str(section_out)):
        handler.data["page.counter"] = 7
    assert ">7<" in section_out.read_text(encoding="utf-8")
    assert renders == []              # the registered default was bypassed
    with handler.live():
        handler.data["page.counter"] = 8
    assert len(renders) == 1          # back to the registered default


def test_outside_a_section_nothing_is_queued():
    renders: list = []
    handler, page = _mounted(renders)
    handler.data["page.counter"] = 5  # logic may run, no render queued
    assert handler._nodes_to_render == {}
    assert renders == []


def test_sections_from_other_threads_are_serialized():
    renders: list = []
    handler, page = _mounted(renders)
    errors: list = []

    def worker(value):
        try:
            with handler.live():
                handler.data["page.counter"] = value
        except Exception as exc:      # noqa: BLE001 - collected for the assert
            errors.append(exc)

    # values all distinct and != the seeded 0: every write fires an event
    threads = [threading.Thread(target=worker, args=(i + 1,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(renders) == 8          # one flush per section, none lost


def test_live_decorator_wraps_the_method_in_a_section():
    renders: list = []
    handler, page = _mounted(renders)

    class App:
        def __init__(self, handler):
            self.handler = handler

        @live
        def on_message(self, value):
            self.handler.data["page.counter"] = value

    App(handler).on_message(42)
    assert len(renders) == 1
    assert ">42<" in renders[0]
