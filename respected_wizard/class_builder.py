from typing import Type, List, Dict
from pathlib import Path
import json

from pydantic import create_model
from pydantic.config import BaseConfig, Extra


class ClassBuilder:

    def __init__(self, schema_uri: str):
        self.schema = self.resolve_schema(schema_uri)
        self.build_classes()

    def build_classes(self):
        self.models = []
        for name, definition in self.schema['$defs'].items():
            props = {}
            for prop_name, prop_attrs in definition['properties'].items():
                prop_type = resolve_type(prop_attrs['type'])
                props[prop_name] = (prop_type, ...)

            self.models.append(
                create_model(
                    name,
                    __config__=config,
                    **props
                )
            )

    def resolve_schema(self, schema_uri: str):
        schema_path = Path(schema_uri)
        with open(schema_path, 'r') as f:
            return json.load(f)


def handle_additional_properties(config: BaseConfig, value) -> BaseConfig:
    if isinstance(value, bool) and not value:
        config.extra = Extra.forbid
    return config


def resolve_type(type_name: str) -> Type:
    """
    currently only supporting primitive types
    """
    if type_name == "number":
        return float
    elif type_name == "string":
        return str
    elif type_name == "boolean":
        return bool
    elif type_name == "array":
        return List
    elif type_name == "object":
        return Dict
    # TODO null?
    else:
        raise Exception("unrecognized type")

# basic_schema = json.load(open('basic_schema.json', 'r'))
# M = create_model("Point", x=(int, ...), y=(int, ...))

c = ClassBuilder('basic_schema.json')
Point = c.models[0]
p = Point(x=2, y=3)
pz = Point(x=2, y=3, z=1)

