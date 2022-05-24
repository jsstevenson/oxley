"""Provide class construction tools."""
from typing import (
    Any,
    Literal,
    Optional,
    Type,
    Dict,
    Type,
    ForwardRef,
    List,
    Set,
    Tuple,
)
from enum import Enum
from pathlib import Path
import json
import logging
import re

from pydantic import create_model
from pydantic.config import BaseConfig, Extra

from respected_wizard.schema_versions import SchemaVersion, SCHEMA_MATCH_PATTERNS
from respected_wizard.typing import resolve_type
from respected_wizard.exceptions import (
    SchemaConversionException,
    UnsupportedSchemaException,
)

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.FileHandler("respected_wizard.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class ClassBuilder:
    def __init__(self, schema_uri: str):
        """
        Args:
            schema_uri: URL pointing to schema
        """
        self.schema = self.resolve_schema(schema_uri)
        self.models: List = []
        self.localns: Dict = {}
        self.contains_forward_refs: Set = set()

    def build_classes(self) -> List:
        """
        Construct classes from requested schema.

        Returns:
            List of Pydantic classes generated from schema
        """
        for name, definition in self.schema[self.def_keyword].items():

            if definition["type"] == "object":
                self.build_object_class(name, definition)
            elif definition["type"] == "string":
                self.build_simple_class(name, definition)

        for model in self.contains_forward_refs:
            model.update_forward_refs(**self.localns)
        self.models = list(self.localns.values())
        return self.models

    def build_simple_class(self, name: str, definition: Dict):
        """
        Construct classes derived from basic primitives (eg strings).
        Currently only supports strings.
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
        self.localns[name] = model

    def _handle_class_deprecation(self, name: str, definition: Dict):
        if definition.get("deprecated"):
            logger.warning(f"Class {name} is deprecated.")

    def build_object_class(self, name: str, definition: Dict):
        """
        Construct object-based class. Updates `self.contains_forward_refs` collection
        if object contains references to other defined objects.
        """
        props = {}
        has_forward_ref = False
        required_props = definition.get("required", set())

        self._handle_class_deprecation(name, definition)

        for prop_name, prop_attrs in definition["properties"].items():
            if "$ref" in prop_attrs:
                prop_type: Any = ForwardRef(self.resolve_ref(prop_attrs["$ref"]))
                has_forward_ref = True
            else:
                prop_type = resolve_type(prop_attrs["type"])

            if "const" in prop_attrs:
                const_value = prop_attrs["const"]
                if not any(
                    [isinstance(const_value, t) for t in (str, int, float, bool)]
                ):
                    raise SchemaConversionException
                else:
                    const_type = Literal[const_value]  # type: ignore
                if prop_name not in required_props:
                    const_type = Optional[const_type]  # type: ignore
                props[prop_name] = (const_type, const_value)
            elif "enum" in prop_attrs:
                enum_type = Enum(
                    prop_name, {str(p).upper(): p for p in prop_attrs["enum"]}, type=str
                )  # type: ignore
                props[prop_name] = (enum_type, None)
            else:
                if prop_name not in required_props and "default" not in prop_attrs:
                    props[prop_name] = (Optional[prop_type], None)  # type: ignore
                else:
                    props[prop_name] = (prop_type, ...)
        config = self.get_configs(definition)
        model = create_model(__model_name=name, __config__=config, **props)  # type: ignore

        self.localns[name] = model
        if has_forward_ref:
            self.contains_forward_refs.add(model)

    def get_configs(self, definition: Dict) -> Type[BaseConfig]:
        """
        Set model configs from definition attributes.

        Currently only supports restricting/allowing/ignoring extra values based on
        additionalProperties value.

        Args:
            definition: item definition from schema

        Returns:
            Class based on BaseConfig with new attributes set, where necessary
        """
        if "additionalProperties" in definition:
            additional_properties = definition["additionalProperties"]
            if additional_properties is False:
                extra_value = Extra.forbid
            elif additional_properties is True:
                extra_value = Extra.allow
            else:
                logger.warning(
                    f"Unrecognized additionalProperties value: {additional_properties}"
                )
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
        with open(schema_path, "r") as f:
            schema = json.load(f)

        schema_version = self.resolve_schema_version(schema.get("$schema", ""))

        if schema_version == SchemaVersion.DRAFT_2020_12:
            self.def_keyword = "$defs"
        elif schema_version == SchemaVersion.DRAFT_07:
            self.def_keyword = "definitions"

        return schema

    def resolve_ref(self, ref: str) -> str:
        """
        Get class name from reference

        Return:
            Class name parsed from reference

        Raise:
            UnsupportedSchemaException: if reference points beyond the document
        """
        leader = f"#/{self.def_keyword}/"
        if not ref.startswith(leader):
            raise UnsupportedSchemaException(
                "External references not currently supported"
            )
        return ref.split(leader)[1]
