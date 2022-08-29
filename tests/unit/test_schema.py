"""Test schema version handler module."""
from pathlib import Path

import pytest

from oxley.exceptions import InvalidSchemaException, UnsupportedSchemaException
from oxley.schema import SchemaVersion, get_schema, resolve_schema_version


def test_resolve_schema_version():
    assert (
        resolve_schema_version("https://json-schema.org/draft/2020-12/schema")
        == SchemaVersion.DRAFT_2020_12
    )
    assert (
        resolve_schema_version("https://www.json-schema.org/draft/2020-12/schema")
        == SchemaVersion.DRAFT_2020_12
    )

    assert (
        resolve_schema_version("http://json-schema.org/draft-07/schema")
        == SchemaVersion.DRAFT_07
    )
    assert (
        resolve_schema_version("https://www.json-schema.org/draft-07/schema")
        == SchemaVersion.DRAFT_07
    )
    assert (
        resolve_schema_version("https://json-schema.org/draft-07/schema")
        == SchemaVersion.DRAFT_07
    )

    # not supported yet
    with pytest.raises(UnsupportedSchemaException):
        resolve_schema_version("https://json-schema.org/draft/2019-09/schema")


def test_get_schema():
    """Test get_schema operations."""
    http_ref = "https://json-schema.org/learn/examples/address.schema.json"
    assert get_schema(http_ref) == {
        "$id": "https://example.com/address.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "description": "An address similar to http://microformats.org/wiki/h-card",
        "type": "object",
        "properties": {
            "post-office-box": {"type": "string"},
            "extended-address": {"type": "string"},
            "street-address": {"type": "string"},
            "locality": {"type": "string"},
            "region": {"type": "string"},
            "postal-code": {"type": "string"},
            "country-name": {"type": "string"},
        },
        "required": ["locality", "region", "country-name"],
        "dependentRequired": {
            "post-office-box": ["street-address"],
            "extended-address": ["street-address"],
        },
    }

    invalid_http_ref = "https://json-schema.org/learn/examples/address.schema.jso"
    with pytest.raises(InvalidSchemaException) as exc_info:
        get_schema(invalid_http_ref)
    assert (
        str(exc_info.value)
        == f"Schema HTTP retrieval from address {invalid_http_ref} failed with "
        f"code {404}"
    )

    path_str_ref = "tests/data/example_schema.json"
    assert get_schema(path_str_ref)

    path_ref = Path("tests") / "data" / "example_schema.json"
    assert get_schema(path_ref)

    incoherent_str_ref = "sdfkljdfk"
    with pytest.raises(InvalidSchemaException) as exc_info:
        get_schema(incoherent_str_ref)
    assert str(exc_info.value) == "Unable to produce valid schema from input object."

    existing_json = {
        "$id": "https://example.com/address.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "description": "An address similar to http://microformats.org/wiki/h-card",
        "type": "object",
        "properties": {
            "post-office-box": {"type": "string"},
        },
    }
    assert get_schema(existing_json) == existing_json

    with pytest.raises(InvalidSchemaException) as exc_info:
        get_schema(("https://json-schema.org/learn/examples/address.schema.json",))  # type: ignore # noqa: E501
    assert str(exc_info.value) == "Unable to produce valid schema from input object."
