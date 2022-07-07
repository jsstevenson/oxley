"""Test pydantic_utils module."""
from typing import Any, Dict, Type

from pydantic.config import Extra

from oxley.pydantic_utils import get_configs


def test_get_configs():
    # test additional properties
    c = get_configs("Point", {"additionalProperties": False}, False)
    assert c.extra == Extra.forbid
    c = get_configs("Point", {"additionalProperties": True}, False)
    assert c.extra == Extra.allow
    c = get_configs("Point", {}, False)
    assert c.extra == Extra.ignore

    # test example
    c = get_configs(
        "HumanCytoband",
        {
            "additionalProperties": False,
            "description": "A character string representing cytobands derived from the *International System for Human Cytogenomic Nomenclature* (ISCN) [guidelines](http://doi.org/10.1159/isbn.978-3-318-06861-0).",
            "type": "string",
            "pattern": "^cen|[pq](ter|([1-9][0-9]*(\\.[1-9][0-9]*)?))$",
            "example": "q22.3",
        },
        False,
    )
    schema = {}
    c.schema_extra(schema, Type)  # type: ignore
    assert schema["example"] == "q22.3"

    # test allow population by field name
    c = get_configs("Point", {}, True)
    assert c.allow_population_by_field_name
