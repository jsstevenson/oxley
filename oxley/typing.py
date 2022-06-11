"""Provide miscellaneous type utilities."""
from typing import List, Optional, Type, TypeVar, Union, get_args, get_origin

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
