"""Provide class construction tools."""
from enum import Enum
from typing import Literal, Type, List, Dict, Type
from pathlib import Path
import json
import logging
import re

from pydantic import create_model
from pydantic.config import BaseConfig, Extra

from respected_wizard import exceptions


logger = logging.getLogger('class_builder')


class SchemaVersion(str, Enum):
    """Define recognized JSONschema versions."""

    DRAFT_07 = "draft-07",
    DRAFT_2020_12 = "draft-2020-12"


SCHEMA_MATCH_PATTERNS = {
    re.compile(r"^http(s)?://(www\.)?json-schema.org/draft/2020-12/schema$"): SchemaVersion.DRAFT_2020_12,
    re.compile(r"^http(s)?://(www\.)?json-schema.org/draft-07/schema$"): SchemaVersion.DRAFT_07
}


class ClassBuilder:

    def __init__(self, schema_uri: str):
        self.schema = self.resolve_schema(schema_uri)
        self.build_classes()

    def build_classes(self):
        self.models = []
        for name, definition in self.schema[self.def_keyword].items():
            props = {}
            for prop_name, prop_attrs in definition['properties'].items():
                prop_type = resolve_type(prop_attrs['type'])
                if 'const' in prop_attrs:
                    const_value = prop_attrs['const']
                    if not any([isinstance(const_value, t) for t in (str, int, float, bool)]):
                        raise exceptions.JSONSchemaConversionException
                    else:
                        const_type = Literal[const_value]  # type: ignore
                    props[prop_name] = (const_type, const_value)
                else:
                    props[prop_name] = (prop_type, ...)

            config = self.get_configs(definition)

            self.models.append(
                create_model(
                    name,
                    __config__=config,
                    **props
                )
            )

    def get_configs(self, definition: Dict) -> Type[BaseConfig]:
        if 'additionalProperties' in definition:
            additional_properties = definition['additionalProperties']
            if additional_properties is False:
                extra_value = Extra.forbid
            elif additional_properties is True:
                extra_value = Extra.allow
            else:
                logger.warning(f'Unrecognized additionalProperties value: {additional_properties}')
                extra_value = Extra.ignore
        else:
            extra_value = Extra.ignore

        class ModifiedConfig(BaseConfig):
            extra: Extra = extra_value

        return ModifiedConfig


    def resolve_schema_version(self, schema_version: str) -> SchemaVersion:
        """
        Get version enum from JSONschema version string.
        """
        for pattern, version in SCHEMA_MATCH_PATTERNS.items():
            if re.match(pattern, schema_version):
                return version
        raise exceptions.UnsupportedJSONSchemaException

    def resolve_schema(self, schema_uri: str):
        schema_path = Path(schema_uri)
        with open(schema_path, 'r') as f:
            schema = json.load(f)

        try:
            schema_version = self.resolve_schema_version(schema.get("$schema", ""))
        except ValueError:
            raise exceptions.UnsupportedJSONSchemaException

        if schema_version == SchemaVersion.DRAFT_2020_12:
            self.def_keyword = '$defs'
        elif schema_version == SchemaVersion.DRAFT_07:
            self.def_keyword = 'definitions'

        return schema


def resolve_type(type_name: str) -> Type:
    """
    currently only supporting primitive types
    """
    if type_name == 'number' or type_name == 'float':
        return float
    elif type_name == 'integer':
        return int
    elif type_name == 'string':
        return str
    elif type_name == 'boolean':
        return bool
    elif type_name == 'array':
        return List
    elif type_name == 'object':
        return Dict
    # TODO null?
    else:
        raise ConversionException('unrecognized type')
