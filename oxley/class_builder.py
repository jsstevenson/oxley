"""Provide class construction tools."""
import json
import logging
import re
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    ForwardRef,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Union,
)

import requests
from pydantic import create_model, validator
from pydantic.class_validators import root_validator
from pydantic.fields import Field, Undefined
from pydantic.main import BaseModel

from .exceptions import (
    InvalidReferenceException,
    SchemaConversionException,
    UnsupportedSchemaException,
)
from .pydantic_utils import get_configs
from .schema_versions import SchemaVersion, resolve_schema_version
from .types import resolve_type

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("pydantic_jsonschema_objects.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


REF_PATTERN = re.compile(r"(.*)#/((definitions)|(\$defs))/(.*)")


class ClassBuilder:
    def __init__(self, schema_uri: str):
        """
        Args:
            schema_uri: URL pointing to schema
        """
        self.schema = self._resolve_schema(schema_uri)
        self.models: List = []
        self.local_ns: Dict = {}
        self.contains_forward_refs: Set = set()
        self.external_ns: Set[str] = set()
        self.external_schemas: List[Tuple[str, Dict]] = []

    def build_classes(self) -> List:
        """
        Construct classes from requested schema.

        Returns:
            List of Pydantic classes generated from schema
        """
        for name, definition in self.schema[self.def_keyword].items():
            self._build_class(name, definition)
        while len(self.external_schemas) > 0:
            external_name, external_definition = self.external_schemas[0]
            self._build_class(external_name, external_definition)
            self.external_schemas = self.external_schemas[1:]

        for model in self.contains_forward_refs:
            model.update_forward_refs(**self.local_ns)
        self.models = list(self.local_ns.values())
        return self.models

    def _build_class(self, name: str, definition: Dict) -> None:
        if definition["type"] == "object":
            self._build_object_class(name, definition)
        elif definition["type"] == "string":
            self._build_primitive_class(name, definition)

    def _build_primitive_class(self, name: str, definition: Dict):
        """
        Construct classes derived from basic primitives (eg strings). Bare strings and
        numbers don't need to come through here, but any class that bounds their
        possible values will. Updates `self.local_ns` with completed class definition.
        Currently only supports strings.

        Args:
            name: class name
            definition: class properties from schema

        Raises:
            UnsupportedSchemaException: if non-string classes are provided.
        """
        attributes = {}
        type_tuple: Tuple = ()
        if definition["type"] == "string":

            type_tuple = (str,)
            if "pattern" in definition:
                pattern = definition["pattern"]

                # handle JS escape sequences
                # TODO: do this more robustly
                pattern = pattern.replace("//", "/")

                @classmethod  # type: ignore
                def __get_validators__(cls):
                    yield cls.validate

                @classmethod  # type: ignore
                def __modify_schema__(cls, field_schema):
                    field_schema.update(pattern=pattern)

                @classmethod  # type: ignore
                def validate(cls, v):
                    if not isinstance(v, str):
                        raise TypeError("string required")
                    m = re.match(pattern, v)
                    if not m:
                        raise ValueError("provided value doesn't match pattern")
                    return cls(v)

                attributes = {
                    "__get_validators__": __get_validators__,
                    "__modify_schema__": __modify_schema__,
                    "validate": validate,
                }

        else:
            raise UnsupportedSchemaException
        model = type(name, type_tuple, attributes)
        self.local_ns[name] = model

    def _build_object_class(self, name: str, definition: Dict):
        """
        Construct object-based class.

        Updates `self.local_ns` to include the completed model.
        Also updates `self.contains_forward_refs` collection if object contains
        references to other defined objects.

        Args:
            name: name of the object class
            definition: dictionary containing class properties

        Raise:
            SchemaConversionException:
             * if unsupported types are provided as consts
        """
        fields: Dict[str, Union[Tuple[Any, Any], Callable]] = {}
        has_forward_ref = False
        required_fields = definition.get("required", set())
        allow_population_by_field_name = False
        validators: Dict = {}

        if definition.get("deprecated") is True:

            def class_deprecation_warning(cls, values):
                logger.warning(f"Class {name} is deprecated.")
                return values

            validators["class_deprecated"] = root_validator(pre=True, allow_reuse=True)(
                class_deprecation_warning
            )

        for prop_name, prop_attrs in definition["properties"].items():
            if "$ref" in prop_attrs:
                field_type: Any = ForwardRef(self._resolve_ref(prop_attrs["$ref"]))
                has_forward_ref = True
            else:
                field_type = resolve_type(prop_attrs["type"])

            field_args = {"description": prop_attrs.get("description")}
            if "default" in prop_attrs:
                field_args["default"] = prop_attrs["default"]
            else:
                field_args["default"] = Undefined

            if prop_name[0] == "_":
                alt_name = prop_name[:]
                field_args["alias"] = alt_name
                allow_population_by_field_name = True

                main_field_name = alt_name[1:]

                def dict(self):
                    d = BaseModel.dict(self)
                    if main_field_name in d:
                        d[alt_name[:]] = d[main_field_name]
                        del d[main_field_name]
                    return d

                prop_name = main_field_name

                fields["dict"] = dict

            if prop_attrs.get("deprecated") is True:

                def property_deprecated_warning(cls, v):
                    logger.warning(f"Property {name}.{prop_name} is deprecated")
                    return v

                validators[f"{prop_name}_deprecated"] = validator(
                    prop_name, allow_reuse=True
                )(property_deprecated_warning)

            if "const" in prop_attrs:
                const_value = prop_attrs["const"]
                if not any(
                    [isinstance(const_value, t) for t in (str, int, float, bool)]
                ):
                    # TODO -- construct complex object consts
                    raise SchemaConversionException
                else:
                    const_type = Literal[const_value]  # type: ignore
                if prop_name not in required_fields:
                    const_type = Optional[const_type]  # type: ignore
                field_args["default"] = const_value
                fields[prop_name] = (const_type, Field(**field_args))
            elif "enum" in prop_attrs:
                vals = {str(p).upper(): p for p in prop_attrs["enum"]}
                enum_type = Enum(prop_name, vals, type=str)  # type: ignore
                if prop_name not in required_fields:
                    enum_type = Optional[enum_type]  # type: ignore
                fields[prop_name] = (enum_type, Field(**field_args))
            else:
                if prop_name not in required_fields:
                    field_type = Optional[field_type]
                fields[prop_name] = (field_type, Field(**field_args))

        config = get_configs(name, definition, allow_population_by_field_name)
        model = create_model(__model_name=name, __config__=config, __validators__=validators, **fields)  # type: ignore
        if "description" in definition:
            model.__doc__ = definition["description"]

        self.local_ns[name] = model
        if has_forward_ref:
            self.contains_forward_refs.add(model)

    def _resolve_schema(self, schema_uri: str) -> Dict:
        """
        Get schema version and set necessary config values.

        Args:
            schema_uri: URL to schema instance

        Returns:
            Schema as dict
        """
        schema_path = Path(schema_uri)
        with open(schema_path, "r") as f:
            schema = json.load(f)

        schema_version = resolve_schema_version(schema.get("$schema", ""))

        if schema_version == SchemaVersion.DRAFT_2020_12:
            self.def_keyword = "$defs"
        elif schema_version == SchemaVersion.DRAFT_07:
            self.def_keyword = "definitions"

        return schema

    def _resolve_ref(self, ref: str) -> str:
        """
        Get class name from reference

        Args:
            ref: complete reference value
            def_keyword: schema definition keyword (`$defs` in recent JSONschema versions)

        Return:
            Class name parsed from reference

        Raise:
            InvalidReferenceException: if reference can't be parsed
        """
        match = re.match(REF_PATTERN, ref)
        if match is None:
            raise InvalidReferenceException("Unable to parse provided reference")
        groups = match.groups()
        name = groups[4]
        if groups[0] != "" and name not in self.external_ns:
            response = requests.get(groups[0])
            if response.status_code != 200:
                raise InvalidReferenceException("Unable to retrieve provided reference")
            response_json = response.json()
            object_definition = response_json[groups[1]][name]
            self.external_schemas.append((name, object_definition))
            self.external_ns.add(name)
        return name
