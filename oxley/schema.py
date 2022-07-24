"""Provide schema version definition and basic resolution utilities."""
import json
import re
from enum import Enum
from pathlib import Path
from typing import Dict, Union
from urllib.parse import urlparse

import requests

from .exceptions import InvalidSchemaException, UnsupportedSchemaException


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


def open_local_schema(schema_path: Path) -> Dict:
    """
    Perform simple retrieval of local JSONschema file.

    Args:
        schema_path: path to schema in local filesystem

    Return:
        schema as Dict
    """
    with open(schema_path, "r") as f:
        schema = json.load(f)
    return schema


def get_schema(schema_input: Union[Path, str, Dict]) -> Dict:
    """
    Get schema given user-provided reference or schema object.

    Args:
        schema_input: reference, path, or raw data composing schema

    Return:
        schema as dict

    Raises:
        InvalidSchemaException if schema construction or retrieval fails
    """
    if isinstance(schema_input, Path):
        return open_local_schema(schema_input)
    elif isinstance(schema_input, str):
        path = Path(schema_input)
        if path.exists():
            return open_local_schema(path)
        else:
            parsed_url = urlparse(schema_input)
            if all([parsed_url.scheme, parsed_url.netloc]):
                response = requests.get(schema_input)
                status_code = response.status_code
                if status_code != 200:
                    raise InvalidSchemaException(
                        f"Schema HTTP retrieval from address {schema_input} failed with code {status_code}"
                    )
                return response.json()
            else:
                raise InvalidSchemaException(
                    "Unable to produce valid schema from input object."
                )
    elif isinstance(schema_input, Dict):
        return schema_input
    else:
        raise InvalidSchemaException(
            "Unable to produce valid schema from input object."
        )
