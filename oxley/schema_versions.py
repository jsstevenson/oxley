"""Provide schema version definition and basic resolution utilities."""
import re
from enum import Enum

from .exceptions import UnsupportedSchemaException


class SchemaVersion(str, Enum):
    """Define recognized JSONschema versions."""

    DRAFT_07 = ("draft-07",)  # TODO tuple?
    DRAFT_2020_12 = "draft-2020-12"


SCHEMA_MATCH_PATTERNS = {
    re.compile(
        r"^https://(www\.)?json-schema.org/draft/2020-12/schema$"
    ): SchemaVersion.DRAFT_2020_12,
    re.compile(
        r"^http(s)?://(www\.)?json-schema.org/draft-07/schema$"
    ): SchemaVersion.DRAFT_07,
}


def resolve_schema_version(schema_version: str) -> SchemaVersion:
    """
    Get version enum from JSONschema version string.

    Args:
        schema_version: URL pointing to schema instance

    Returns:
        Enum corresponding to schema version value

    Raises:
        UnsupportedSchemaException: if schema_version is anything other than
        supported versions.
    """
    for pattern, version in SCHEMA_MATCH_PATTERNS.items():
        if re.match(pattern, schema_version):
            return version
    raise UnsupportedSchemaException
