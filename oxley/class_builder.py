"""Provide class construction tools."""
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
    Type,
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
    SchemaParseException,
    UnsupportedSchemaException,
)
from .pydantic_utils import get_configs
from .schema import SchemaVersion, get_schema, resolve_schema_version
from .types import build_number_class, convert_type_name, get_typeclass, is_number_type
from .validators import (
    create_array_contains_validator,
    create_array_length_validator,
    create_array_unique_validator,
    create_string_regex_validator,
    create_tuple_validator,
)

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("oxley.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


REF_PATTERN = re.compile(r"(.*)#/((definitions)|(\$defs))/(.*)")


FieldsType = Dict[str, Union[Callable, Tuple]]


class ClassBuilder:
    def __init__(self, schema: Union[Path, str, Dict]):
        """
        Args:
            schema_uri: URL pointing to schema
        """
        self.schema = self._resolve_schema(schema)
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
        """
        Build Pydantic class from definition.
        Subtly different from building a type, which might not need a separate Pydantic
        instance. Every set of arguments received here should be stored by child methods
        in one of the `namespace` state variables, and returned by the `build_classes`
        method.

        Args:
            name: class name
            definition: properties
        """
        if definition["type"] == "object":
            self._build_object_class(name, definition)
        elif definition["type"] in ["string", "number", "integer"]:
            self._build_primitive_class(name, definition)

    def _resolve_ref(self, ref: str) -> str:
        """
        Get class name from reference and update external schemas tracking

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

    def _build_string_class(self, name: str, definition: dict) -> Tuple[Tuple, Dict]:
        """
        Provide components for a Pydantic-compatible class object for specialized
        string properties.

        Args:
            name: class name
            definition: property definition

        Return:
            type tuple `(str,)` and a dictionary containing attributes.
        """
        type_tuple = (str,)
        attributes = {}
        if "pattern" in definition:
            pattern = definition["pattern"]

            # handle JS escape sequences
            # TODO: do this more robustly
            # https://github.com/jsstevenson/oxley/issues/1
            pattern = pattern.replace("//", "/")

            def __get_validators__(cls):
                yield cls.validate

            def __modify_schema__(cls, field_schema):
                field_schema.update(pattern=pattern)

            attributes = {
                "__get_validators__": classmethod(__get_validators__),
                "__modify_schema__": classmethod(__modify_schema__),
                "validate": validator(name, allow_reuse=True)(
                    create_string_regex_validator(pattern)
                ),
            }

        return type_tuple, attributes

    def _build_primitive_class(self, name: str, definition: Dict) -> None:
        """
        Construct classes derived from basic primitives (eg strings). Bare strings and
        numbers don't need to come through here, but any class that bounds their
        possible values will. Updates `self.local_ns` with completed class definition.

        Args:
            name: class name
            definition: class properties from schema

        Raises:
            UnsupportedSchemaException: if non-string classes are provided.
        """
        attributes = {}
        type_tuple: Tuple = ()
        if definition["type"] == "string":
            type_tuple, attributes = self._build_string_class(name, definition)
        elif definition["type"] in ["number", "integer"]:
            type_tuple = (build_number_class(definition),)
        else:
            raise UnsupportedSchemaException
        model = type(name, type_tuple, attributes)
        self.local_ns[name] = model

    def _build_array_property(
        self, prop_name: str, prop_attrs: Dict
    ) -> Tuple[Type, Dict, bool]:
        """
        Construct component parts for array property.

        Args:
            prop_name: field name of property
            prop_attrs: array property attributes

        Return:
            Type tuple, validators dictionary, forward ref flag
        """
        validators = {}
        has_forward_ref = False

        if "contains" in prop_attrs:
            validate_contains = create_array_contains_validator(
                prop_attrs["contains"],
                prop_attrs.get("minContains"),
                prop_attrs.get("maxContains"),
            )
            validators[f"validate_{prop_name}_contains"] = validator(
                prop_name, allow_reuse=True
            )(validate_contains)
            array_type = List

        if "prefixItems" in prop_attrs:
            # Pydantic doesn't have a list type that conforms to JSONschema tuples --
            # so we have to recreate the behavior by manually validating each value
            validate_tuple = create_tuple_validator(prop_attrs)
            validators[f"validate_{prop_name}_tuple"] = validator(
                prop_name, allow_reuse=True
            )(validate_tuple)
            array_type = List
        elif "items" in prop_attrs:
            if "$ref" in prop_attrs["items"]:
                item_type: Any = ForwardRef(
                    self._resolve_ref(prop_attrs["items"]["$ref"])
                )
                has_forward_ref = True
            elif "type" in prop_attrs["items"]:
                raw_array_type = prop_attrs["items"]["type"]
                item_type = convert_type_name(raw_array_type)
                if is_number_type(item_type):
                    item_type = (build_number_class(prop_attrs["items"]),)
            else:
                raise SchemaParseException(
                    "`items` property, if it exists, should include either reference or `type` properties"
                )
            array_type = List[item_type]  # type: ignore
        else:
            array_type = List

        if "minItems" in prop_attrs or "maxItems" in prop_attrs:
            length_validator = create_array_length_validator(
                prop_attrs.get("minItems"), prop_attrs.get("maxItems")
            )
            validators[f"validate_{prop_name}_length"] = validator(
                prop_name, allow_reuse=True
            )(length_validator)

        if prop_attrs.get("uniqueItems") is True:
            unique_validator = create_array_unique_validator()
            validators[f"validate_{prop_name}_unique"] = validator(
                prop_name, allow_reuse=True
            )(unique_validator)

        return array_type, validators, has_forward_ref

    def _build_property(
        self, class_name: str, prop_name: str, prop_attrs: Dict, required_field: bool
    ) -> Tuple[FieldsType, Dict[str, Callable], bool, bool]:
        """
        Construct individual object property.

        Args:
            class_name: name of class
            prop_name: name of property
            prop_attrs: property definition
            required_field: if True, field is required, optional otherwise

        Return:
            Fields Types, validators, and flags for constructor configs

        Raise:
            SchemaConversionException: if unsupported types are provided as consts
        """
        has_forward_ref = False
        allow_population_by_field_name = False
        validators = {}
        fields: FieldsType = {}

        if "$ref" in prop_attrs:
            field_type: Any = ForwardRef(self._resolve_ref(prop_attrs["$ref"]))
            has_forward_ref = True
        else:
            raw_type_value = prop_attrs["type"]
            if raw_type_value == "array":
                (
                    field_type,
                    arr_validators,
                    arr_has_forward_ref,
                ) = self._build_array_property(prop_name, prop_attrs)
                validators.update(arr_validators)
                has_forward_ref |= arr_has_forward_ref
            elif raw_type_value in ("number", "integer"):
                field_type = build_number_class(prop_attrs)
            else:
                field_type = convert_type_name(raw_type_value)

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
                logger.warning(f"Property {class_name}.{prop_name} is deprecated")
                return v

            validators[f"{prop_name}_deprecated"] = validator(
                prop_name, allow_reuse=True
            )(property_deprecated_warning)

        if "const" in prop_attrs:
            const_value = prop_attrs["const"]
            if not any([isinstance(const_value, t) for t in (str, int, float, bool)]):
                # TODO -- construct complex object consts
                raise SchemaConversionException
            else:
                field_type = Literal[const_value]  # type: ignore
            field_args["default"] = const_value
        elif "enum" in prop_attrs:
            vals = {str(p).upper(): p for p in prop_attrs["enum"]}
            field_type = Enum(prop_name, vals, type=str)  # type: ignore

        if not required_field:
            field_type = Optional[field_type]

        fields[prop_name] = (field_type, Field(**field_args))  # type: ignore
        return fields, validators, has_forward_ref, allow_population_by_field_name

    def _build_object_class(self, name: str, definition: Dict) -> None:
        """
        Construct object-based class.

        Updates `self.local_ns` to include the completed model.
        Also updates `self.contains_forward_refs` collection if object contains
        references to other defined objects.

        Args:
            name: name of the object class
            definition: dictionary containing class properties
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
            field_required = prop_name in required_fields
            (
                new_fields,
                new_validators,
                prop_fwd_ref,
                prop_pop_field_name,
            ) = self._build_property(name, prop_name, prop_attrs, field_required)
            fields.update(new_fields)
            validators.update(new_validators)
            has_forward_ref |= prop_fwd_ref
            allow_population_by_field_name |= prop_pop_field_name

        config = get_configs(name, definition, allow_population_by_field_name)
        model = create_model(
            __model_name=name, __config__=config, __validators__=validators, **fields
        )  # type: ignore
        if "description" in definition:
            model.__doc__ = definition["description"]

        self.local_ns[name] = model
        if has_forward_ref:
            self.contains_forward_refs.add(model)

    def _resolve_schema(self, schema_input: Union[Path, str, Dict]) -> Dict:
        """
        Get schema version and set necessary config values.
        Tries to resolve input arg in the following order:
          * as a Path object
          * as a Path-like string to a local file
          * as an HTTP reference to a JSONschema document
          * as a Dict constructed from a JSONschema document

        Args:
            schema_input: class builder input. Could be a Path or pathlike object to a local file,
                an HTTP URL, or a plain Dict built from JSON input elsewhere.

        Returns:
            Schema as dict
        """
        schema = get_schema(schema_input)
        schema_version = resolve_schema_version(schema.get("$schema", ""))

        if schema_version == SchemaVersion.DRAFT_2020_12:
            self.def_keyword = "$defs"
        elif schema_version == SchemaVersion.DRAFT_07:
            self.def_keyword = "definitions"

        return schema
