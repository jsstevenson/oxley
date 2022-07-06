"""Test schema version handler module."""
import pytest

from oxley.exceptions import UnsupportedSchemaException
from oxley.schema_versions import SchemaVersion, resolve_schema_version


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
