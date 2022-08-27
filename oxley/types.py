"""Provide miscellaneous type utilities."""
import re
from enum import Enum
from inspect import getmro
from string import ascii_uppercase
from typing import Dict, List, Optional, Type, TypeVar, Union, get_args, get_origin

from pydantic import StrictFloat, StrictInt

from .exceptions import SchemaConversionException

TYPE_CONVERSION_TABLE = {
    "number": Union[StrictFloat, StrictInt],
    "integer": StrictInt,
    "string": str,
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": None,
}


def convert_type_name(type_value: Union[str, List[str]]) -> Optional[Type]:
    """
    Convert JSON type name to Python type.

    Args:
        type_value: value of object type property -- either a string for a single type,
            or a list for a union. Should consist only of JSON primitive types.

    Return:
        Corresponding Pydantic-compatible Type -- which can include None for null
        properties.

    Raise:
        SchemaConversionException if unrecognized types are encountered.
    """
    if type_value is None:
        return None
    elif isinstance(type_value, List):
        union_types = tuple([convert_type_name(t) for t in type_value])
        return Union[union_types]  # type: ignore
    elif type_value in TYPE_CONVERSION_TABLE:
        return TYPE_CONVERSION_TABLE[type_value]
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


def is_union_type(field_type: Type) -> bool:
    """
    Check if type is a Union.

    Args:
        field_type: complete field type

    Return:
        True if type is a Union, False otherwise
    """
    return get_origin(field_type) is Union


def is_number_type(defined_type: Type) -> bool:
    """
    Check if type is a number. Intended to match both ints/floats, Pydantic strict
    numbers, and Unions covering the above.

    Args:
        defined_type: should be a Type instance (not a JSONschema field definition)

    Return:
        true if type is a number or a compound containing all number types
    """
    if is_union_type(defined_type):
        return all([is_number_type(subtype) for subtype in get_args(defined_type)])
    else:
        return (int in getmro(defined_type)) or (float in getmro(defined_type))


JSONSchemaClass = TypeVar("JSONSchemaClass")


def get_enum_value_types(enum_definition: List[Union[str, int, float, bool]]) -> Type:
    """
    Get type for Enum type definition.

    Args:
        enum_definition: the value of the schema item `enum` field, i.e., the
        permissible enum values

    Return:
        The Python type corresponding to the enum values

    Raises:
        SchemaConversionException: if types aren't uniform are aren't primitives.
            Unless I've missed something, proper Python enums require all values to
            be the same type, which isn't true in JSONschema.
    """
    value_types = [type(p) for p in enum_definition]
    if value_types.count(value_types[0]) != len(value_types):
        raise SchemaConversionException("Enum values must all be the same type")
    if value_types[0] not in (str, int, float, bool):
        raise SchemaConversionException(
            f"Unable to construct enum from type {value_types[0]}. Must be one of "
            "{`str`, `int`, `float`, `bool`}"
        )
    return value_types


def get_enum_type(field_name: str, field_definition: Dict) -> Type[Enum]:
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
    try:
        value_types = get_enum_value_types(field_definition["enum"])
    except SchemaConversionException:
        raise

    prior_keys = []

    def make_enum_key(name: Union[str, int, float, bool]):
        """
        Hacky way of coercing a legal key out of an enum value
        """
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
        field_name,
        {make_enum_key(p): p for p in field_definition["enum"]},
        type=value_types[0],
    )
    return enum_type
