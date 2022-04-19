"""Provide class construction tools."""
from typing import Literal, Type, List, Dict, Type, ForwardRef
from pathlib import Path
import json
import logging
import re

from pydantic import create_model
from pydantic.config import BaseConfig, Extra

from respected_wizard.schema_versions import SchemaVersion, SCHEMA_MATCH_PATTERNS
from respected_wizard.exceptions import SchemaConversionException, \
    UnsupportedSchemaException


logger = logging.getLogger('class_builder')


class ClassBuilder:

    def __init__(self, schema_uri: str):
        """
        Args:
            schema_uri: URL pointing to schema
        """
        self.schema = self.resolve_schema(schema_uri)
        self.models = []
        self.localns = {}
        self.contains_forward_refs = set()
        self.build_classes()

    def build_classes(self):
        """
        Construct classes from requested schema.
        """
        for name, definition in self.schema[self.def_keyword].items():
            props = {}
            forward_ref = False
            for prop_name, prop_attrs in definition['properties'].items():
                if '$ref' in prop_attrs:
                    prop_type = ForwardRef(self.resolve_ref(prop_attrs['$ref']))
                    forward_ref = True
                else:
                    prop_type = resolve_type(prop_attrs['type'])
                if 'const' in prop_attrs:
                    const_value = prop_attrs['const']
                    if not any([isinstance(const_value, t) for t in (str, int, float, bool)]):
                        raise SchemaConversionException
                    else:
                        const_type = Literal[const_value]  # type: ignore
                    props[prop_name] = (const_type, const_value)
                else:
                    props[prop_name] = (prop_type, ...)

            config = self.get_configs(definition)
            model = create_model(name, __config__=config, **props)

            self.localns[name] = model
            if forward_ref:
                self.contains_forward_refs.add(model)
        for model in self.contains_forward_refs:
            model.update_forward_refs(**self.localns)
        self.models = list(self.localns.values())

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

    def resolve_schema(self, schema_uri: str) -> Dict:
        """
        Get schema version and set necessary config values.

        Args:
            schema_uri: URL to schema instance

        Returns:
            Schema as dict
        """
        schema_path = Path(schema_uri)
        with open(schema_path, 'r') as f:
            schema = json.load(f)

        schema_version = self.resolve_schema_version(schema.get('$schema', ''))

        if schema_version == SchemaVersion.DRAFT_2020_12:
            self.def_keyword = '$defs'
        elif schema_version == SchemaVersion.DRAFT_07:
            self.def_keyword = 'definitions'

        return schema

    def resolve_ref(self, ref: str) -> str:
        """
        Get class name from reference

        Return:
            Class name parsed from reference

        Raise:
            UnsupportedSchemaException: if reference points beyond the document
        """
        leader = f'#/{self.def_keyword}/'
        if not ref.startswith(leader):
            raise UnsupportedSchemaException(
                'External references not currently supported')
        return ref.split(leader)[1]


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
        raise SchemaConversionException('unrecognized type')



