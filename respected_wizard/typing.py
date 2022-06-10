"""Provide miscellaneous type utilities."""
from typing import Optional, Type, List, Union, get_origin, get_args, TypeVar

from respected_wizard.exceptions import SchemaConversionException


def resolve_type(type_value: Union[str, List[str]]) -> Optional[Type]:
    """
    Convert JSON primitive type name to Python type.

    Args:
        type_value: value of object type property -- either a string for a single type,
            or a list for a union. Should consist only of JSON primitive types.

    Return:
        Either a Type or None

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


def is_optional_type(field: Type) -> bool:
    """Check if type is Optional."""
    return get_origin(field) is Union and type(None) in get_args(field)


JSONSchemaClass = TypeVar("JSONSchemaClass")
