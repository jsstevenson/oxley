"""Provide schema version definition and basic resolution utilities."""
import re
from enum import Enum


class SchemaVersion(str, Enum):
    """Define recognized JSONschema versions."""

    DRAFT_07 = "draft-07",
    DRAFT_2020_12 = "draft-2020-12"


SCHEMA_MATCH_PATTERNS = {
    re.compile(r"^http(s)?://(www\.)?json-schema.org/draft/2020-12/schema$"): SchemaVersion.DRAFT_2020_12,
    re.compile(r"^http(s)?://(www\.)?json-schema.org/draft-07/schema$"): SchemaVersion.DRAFT_07
}
