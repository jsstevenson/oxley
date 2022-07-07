"""Provide miscellaneous type utilities."""
import re
from enum import Enum
from string import ascii_uppercase
from typing import Dict, List, Optional, Type, TypeVar, Union, get_args, get_origin

from .exceptions import SchemaConversionException


def resolve_type(type_value: Union[str, List[str]]) -> Optional[Type]:
    """
    Convert JSON primitive type name to Python type.

    Args:
        type_value: value of object type property -- either a string for a single type,
            or a list for a union. Should consist only of JSON primitive types.

    Return:
        Corresponding Pydantic-compatible Type -- which can include None for null
        properties.

    Raise:
        SchemaConversionException if unrecognized types are encountered.
    """
    if isinstance(type_value, List):
        union_types = tuple([resolve_type(t) for t in type_value])
        return Union[union_types]  # type: ignore
    if type_value == "number" or type_value == "float":
        return float
    elif type_value == "integer":
        return int
    elif type_value == "string":
        return str
    elif type_value == "boolean":
        return bool
    elif type_value == "array":
        return list
    elif type_value == "object":
        return dict
    elif type_value == None or type_value == "null":
        return None
    else:
        raise SchemaConversionException("unrecognized type")


def is_optional_type(field_type: Type) -> bool:
    """
    Check if type is Optional.

    Args:
        field_type: complete field type

    Return:
        True if type is nullable, False otherwise
    """
    return get_origin(field_type) is Union and type(None) in get_args(field_type)


JSONSchemaClass = TypeVar("JSONSchemaClass")


def build_enum(field_name: str, field_definition: Dict) -> Type[Enum]:
    """
    Construct enum type from field definition.
    Currently only works with primitive types, and requires type uniformity.

    Args:
        field_name: name to use for enum class
        field_definition: definition of field

    Return:
        Enum subclass constraining values to pre-defined options

    Raise:
        SchemaConversionException: if multiple types given in enum values, if given
        non-primitive types, or if enumerable names can't be generated
    """
    value_types = [type(p) for p in field_definition["enum"]]
    if value_types.count(value_types[0]) != len(value_types):
        raise SchemaConversionException("Enum values must all be the same type")
    if value_types[0] not in (str, int, float, bool):
        raise SchemaConversionException(
            f"Unable to construct enum from type {value_types[0]}. Must be one of "
            "{`str`, `int`, `float`, `bool`}"
        )

    prior_keys = []

    def make_enum_key(name: Union[str, int, float, bool]):
        key = re.sub(r"\W|^(?=\d)", "_", str(name).upper())
        if not key or key not in prior_keys:
            prior_keys.append(key)
            return key
        for char in ascii_uppercase:
            new_key = key + "_" + char
            if new_key not in prior_keys:
                prior_keys.append(new_key)
                return new_key
        else:
            raise SchemaConversionException(
                f"Unable to make enum key from provided name: {key}"
            )

    enum_type = Enum(  # type: ignore
        field_name, {make_enum_key(p): p for p in field_definition["enum"]}
    )
    return enum_type
