# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""JSON grammar documents declared on a builder class (issue #50).

``_grammar_documents`` names ``builder_grammar`` 1.1 documents of a
class; ``_decorated_elements`` says whether its decorated elements are
used. Grammars compose parent first; a later definition of an element
replaces the earlier one entirely, data-elements included.

The documents under ``fixtures/class_grammar/`` are shared with
genro-builders-js: ``expected_base.json`` and ``expected_sub.json`` are
the composed grammars of ``FixtureBase`` and ``FixtureSub`` below, the
document both implementations must produce for the same chain.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from genro_builders import BuilderBase
from genro_builders.builder import element
from genro_builders.builder._grammar_export import _class_schema_to_grammar_document
from genro_builders.contrib.html import HtmlBuilder

FIXTURES = Path(__file__).parent / "fixtures" / "class_grammar"


class FixtureBase(BuilderBase):
    _name = "fixture_base"
    _grammar_documents = ("fixtures/class_grammar/base.json",)


class FixtureSub(FixtureBase):
    _name = "fixture_sub"
    _grammar_documents = (
        "fixtures/class_grammar/redefine_data_elements.json",
        "fixtures/class_grammar/add_element.json",
    )


def _export(cls: type) -> dict:
    return json.loads(json.dumps(_class_schema_to_grammar_document(cls)))


def _parameters(cls: type, tag: str) -> list[dict]:
    return _export(cls)["elements"][tag]["attributes"]["parameters"]


def _schema_attrs(cls: type, tag: str) -> dict:
    attrs = dict(cls._class_schema.get_node(tag).attr)
    attrs.pop("_cached_info", None)
    return attrs


def _document(path: Path, elements: dict) -> Path:
    path.write_text(json.dumps({
        "document_format": {"name": "builder_grammar", "version": "1.1"},
        "grammar": {"name": path.stem, "version": None, "title": None, "description": None},
        "abstracts": {},
        "elements": elements,
    }))
    return path


# ---------------------------------------------------------------------------
# A class document enters _class_schema; the rest is inherited unchanged
# ---------------------------------------------------------------------------


def test_class_document_elements_enter_class_schema() -> None:
    schema = FixtureBase._class_schema
    for tag in ("group", "item", "panel", "dataSetter", "dataFormula", "dataController"):
        assert schema.get_node(tag) is not None, tag
    assert FixtureBase._class_schema["_abstracts"].get_node("flow") is not None
    item = schema.get_node("item")
    assert item.get_attr("ns") == "fx"
    assert item.get_attr("parent_tags") == "group"
    assert item.get_attr("declared_names") == {"code", "level"}
    assert schema.get_node("group").get_attr("collection_key") == "code"


def test_parent_elements_not_redefined_are_inherited_unchanged() -> None:
    for tag in ("group", "item"):
        assert _schema_attrs(FixtureSub, tag) == _schema_attrs(FixtureBase, tag)
    assert _export(FixtureSub)["abstracts"] == _export(FixtureBase)["abstracts"]


def test_loaded_signature_validates_calls() -> None:
    builder = FixtureBase()
    group = builder.source.group()
    group.item(code="a", level=2)
    with pytest.raises(ValueError, match="level"):
        group.item(code="b", level=9)
    with pytest.raises(ValueError, match="does not accept 'color'"):
        group.item(code="c", color="red")
    with pytest.raises(ValueError, match="required attribute 'code'"):
        group.item(level=1)


# ---------------------------------------------------------------------------
# Data-elements redefined by a subclass
# ---------------------------------------------------------------------------


def test_redefined_data_setter_has_only_the_new_parameters() -> None:
    assert [p["name"] for p in _parameters(FixtureSub, "dataSetter")] == [
        "destination_path", "value", "attr",
    ]
    assert FixtureSub._class_schema.get_node("dataSetter").get_attr(
        "declared_names") == {"destination_path", "value"}
    # The parent keeps the BuilderBase definition.
    assert [p["name"] for p in _parameters(FixtureBase, "dataSetter")] == [
        "destination", "value", "attr",
    ]


def test_redefined_data_setter_maps_positional_fields() -> None:
    builder = FixtureSub()
    node = builder.source.dataSetter("customer.name", "Mario")
    assert node.attr["destination_path"] == "customer.name"
    assert node.attr["value"] == "Mario"
    assert "destination" not in node.attr
    with pytest.raises(ValueError, match="required attribute 'destination_path'"):
        builder.source.dataSetter(destination="customer.name")


@pytest.mark.parametrize("tag", ["dataFormula", "dataController"])
def test_redefined_data_elements_have_one_var_keyword(tag: str) -> None:
    kinds = [p["kind"] for p in _parameters(FixtureSub, tag)]
    assert kinds.count("var_keyword") == 1
    assert FixtureSub._class_schema.get_node(tag).get_attr("accepts_var_keyword") is True


def test_decorated_redefinition_replaces_a_data_element() -> None:
    class Dialect(HtmlBuilder):
        @element()
        def dataSetter(self, destination_path, value=None, **attr): ...

    assert Dialect._class_schema.get_node("dataSetter").get_attr(
        "declared_names") == {"destination_path", "value"}
    assert HtmlBuilder._class_schema.get_node("dataSetter").get_attr(
        "declared_names") == {"destination", "value"}


# ---------------------------------------------------------------------------
# Replace, never merge
# ---------------------------------------------------------------------------


def test_redefined_element_keeps_nothing_of_the_parent_definition() -> None:
    attrs = _schema_attrs(FixtureSub, "panel")
    for key in ("sub_tags", "parent_tags", "_meta", "ns", "node_label"):
        assert attrs.get(key) is None, key
    assert attrs["inherits_from"] == ""
    info = FixtureSub()._get_schema_info("panel")
    assert "sub_tags_compiled" not in info
    assert "parent_tags_compiled" not in info
    # The parent definition is untouched, inheritance from ``flow`` included.
    parent_info = FixtureBase()._get_schema_info("panel")
    assert parent_info["sub_tags"] == "item,panel"
    assert parent_info["_meta"] == {"render_tag": "section"}


# ---------------------------------------------------------------------------
# The decorator setting
# ---------------------------------------------------------------------------


def test_decorated_elements_off_are_absent() -> None:
    class JsonOnly(FixtureBase):
        _decorated_elements = False

        @element()
        def extra(self, **kwargs): ...

    assert JsonOnly._class_schema.get_node("extra") is None
    assert "extra" not in JsonOnly.__dict__


def test_decorated_elements_on_are_present() -> None:
    class Decorated(FixtureBase):
        _decorated_elements = True

        @element()
        def extra(self, **kwargs): ...

    class DefaultOn(FixtureBase):
        @element()
        def extra(self, **kwargs): ...

    assert Decorated._class_schema.get_node("extra") is not None
    assert DefaultOn._class_schema.get_node("extra") is not None


def test_decorated_elements_setting_is_per_class() -> None:
    class JsonOnly(FixtureBase):
        _decorated_elements = False

    class Child(JsonOnly):
        @element()
        def extra(self, **kwargs): ...

    assert Child._class_schema.get_node("extra") is not None


def test_document_replaces_a_decorator_of_the_same_class(tmp_path: Path) -> None:
    doc = _document(tmp_path / "box.json", {"box": {
        "sub_tags": "",
        "attributes": {"parameters": [
            {"name": "size", "kind": "positional_or_keyword", "role": "attribute",
             "annotation": None, "has_default": True, "default": 1},
        ]},
    }})

    class Both(BuilderBase):
        _grammar_documents = (str(doc),)

        @element(sub_tags="*", ns="x", _meta={"render_tag": "div"})
        def box(self, colour, **kwargs): ...

    attrs = _schema_attrs(Both, "box")
    assert attrs["sub_tags"] == ""
    assert attrs["declared_names"] == {"size"}
    assert attrs["accepts_var_keyword"] is False
    for key in ("ns", "_meta", "declaration_signature"):
        assert attrs.get(key) is None, key
    assert [p["name"] for p in _parameters(Both, "box")] == ["size"]


def test_class_layers_decorators_then_documents(tmp_path: Path) -> None:
    doc = _document(tmp_path / "layer.json", {
        "box": {"sub_tags": "b"},
        "shelf": {"sub_tags": "box"},
    })

    class Layered(BuilderBase):
        _grammar_documents = (str(doc),)

        @element(sub_tags="a")
        def box(self, **kwargs): ...

        @element(sub_tags="")
        def label(self, **kwargs): ...

    schema = Layered._class_schema
    assert schema.get_node("box").get_attr("sub_tags") == "b"
    assert schema.get_node("label").get_attr("sub_tags") == ""
    assert schema.get_node("shelf").get_attr("sub_tags") == "box"
    labels = [n.label for n in schema if not n.label.startswith("_")]
    assert labels.index("box") < labels.index("label") < labels.index("shelf")


# ---------------------------------------------------------------------------
# Composition order
# ---------------------------------------------------------------------------


def test_documents_of_one_class_compose_in_declared_order(tmp_path: Path) -> None:
    first = _document(tmp_path / "first.json", {"box": {"sub_tags": "a"}})
    second = _document(tmp_path / "second.json", {"box": {"sub_tags": "b"}})

    class FirstThenSecond(BuilderBase):
        _grammar_documents = (str(first), str(second))

    class SecondThenFirst(BuilderBase):
        _grammar_documents = (str(second), str(first))

    assert FirstThenSecond._class_schema.get_node("box").get_attr("sub_tags") == "b"
    assert SecondThenFirst._class_schema.get_node("box").get_attr("sub_tags") == "a"


def test_mro_composes_parent_first(tmp_path: Path) -> None:
    child_doc = _document(tmp_path / "child.json", {"item": {"sub_tags": "*"}})

    class Child(FixtureSub):
        _grammar_documents = (str(child_doc),)

    class GrandChild(Child):
        @element(sub_tags="")
        def badge(self, **kwargs): ...

    # base.json -> redefine_data_elements.json -> add_element.json
    # -> child.json -> GrandChild decorators (a later class).
    assert Child._class_schema.get_node("item").get_attr("sub_tags") == "*"
    assert Child._class_schema.get_node("item").get_attr("ns") is None
    assert Child._class_schema.get_node("badge").get_attr("declared_names") == {
        "node_value", "tone",
    }
    assert GrandChild._class_schema.get_node("badge").get_attr("declared_names") == set()
    assert GrandChild._class_schema.get_node("item").get_attr("sub_tags") == "*"


# ---------------------------------------------------------------------------
# Export 1.1 reads back as the same grammar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source", [FixtureSub, HtmlBuilder])
def test_export_reads_back_as_the_same_grammar(source: type, tmp_path: Path) -> None:
    exported = tmp_path / "exported.json"
    source.to_grammar(exported)
    document = json.loads(exported.read_text())
    assert document["document_format"] == {"name": "builder_grammar", "version": "1.1"}

    class ReadBack(BuilderBase):
        _grammar_documents = (str(exported),)

    again = _export(ReadBack)
    assert again["abstracts"] == document["abstracts"]
    assert again["elements"] == document["elements"]


def test_decorated_export_writes_attributes() -> None:
    parameters = _parameters(HtmlBuilder, "dataFormula")
    assert parameters == [
        {"name": "destination", "kind": "positional_or_keyword", "role": "attribute",
         "annotation": {"kind": "type", "module": "builtins", "name": "str"},
         "has_default": False},
        {"name": "func", "kind": "positional_or_keyword", "role": "attribute",
         "annotation": {"kind": "union", "items": [
             {"kind": "type", "module": "builtins", "name": "str"},
             {"kind": "type", "module": "collections.abc", "name": "Callable"}]},
         "has_default": False},
        {"name": "kwargs", "kind": "var_keyword", "role": "attribute",
         "annotation": None, "has_default": False},
    ]


# ---------------------------------------------------------------------------
# Shared fixtures: same composed grammar as genro-builders-js
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("cls", "expected"), [
    (FixtureBase, "expected_base.json"),
    (FixtureSub, "expected_sub.json"),
])
def test_composed_grammar_matches_shared_fixture(cls: type, expected: str) -> None:
    assert _export(cls) == json.loads((FIXTURES / expected).read_text())


# ---------------------------------------------------------------------------
# Document validation
# ---------------------------------------------------------------------------


def test_document_version_other_than_1_1_is_rejected(tmp_path: Path) -> None:
    doc = tmp_path / "old.json"
    data = json.loads((FIXTURES / "add_element.json").read_text())
    data["document_format"]["version"] = "1.0"
    doc.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="version 1.1"):
        class Old(BuilderBase):
            _grammar_documents = (str(doc),)


def test_unknown_entry_field_is_rejected(tmp_path: Path) -> None:
    doc = _document(tmp_path / "bad.json", {"box": {"sub_tags": "", "colour": "red"}})
    with pytest.raises(ValueError, match="unknown fields"):
        class Bad(BuilderBase):
            _grammar_documents = (str(doc),)


def test_single_path_instead_of_tuple_is_rejected() -> None:
    with pytest.raises(TypeError, match="tuple of paths"):
        class Single(BuilderBase):
            _grammar_documents = "fixtures/class_grammar/base.json"


def test_redefined_abstract_reaches_inheriting_elements(tmp_path: Path) -> None:
    doc = tmp_path / "flow.json"
    doc.write_text(json.dumps({
        "document_format": {"name": "builder_grammar", "version": "1.1"},
        "grammar": {"name": "flow", "version": None, "title": None, "description": None},
        "abstracts": {"flow": {"sub_tags": "item"}},
        "elements": {},
    }))
    assert FixtureBase()._get_schema_info("panel")["sub_tags"] == "item,panel"

    class NarrowFlow(FixtureBase):
        _grammar_documents = (str(doc),)

    assert NarrowFlow()._get_schema_info("panel")["sub_tags"] == "item"
