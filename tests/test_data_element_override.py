"""Contract: a dialect may specialize a data-element's authoring grammar."""
import pytest

from genro_builders.builder import element
from genro_builders.contrib.html.html_builder import HtmlBuilder


class GuiBuilder(HtmlBuilder):
    @element(_meta={"data_element": True})
    def dataFormula(self, destination: str, formula: str, **kwargs): ...


class ChildGuiBuilder(GuiBuilder):
    pass


@pytest.mark.parametrize("builder_class", [GuiBuilder, ChildGuiBuilder])
def test_data_element_override_survives_inheritance(builder_class):
    builder = builder_class("main")
    builder.source.dataFormula(destination="result", formula="value * 2", value="^value")
    node = builder.source.get_nodes()[0]
    assert node.attr["formula"] == "value * 2"
    assert "func" not in node.attr
    with pytest.raises(ValueError, match="formula"):
        builder.source.dataFormula(destination="result", func="old")


def test_generic_html_keeps_its_original_data_formula():
    builder = HtmlBuilder("main")
    builder.source.dataFormula(destination="result", func="compute", value="^value")
    assert builder.source.get_nodes()[0].attr["func"] == "compute"
