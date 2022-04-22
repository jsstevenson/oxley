"""Provide miscellaneous type utilities."""
from typing import Type, List, Dict, Union, get_origin, get_args, TypeVar

from respected_wizard.exceptions import SchemaConversionException


def resolve_type(type_name: str) -> Type:
    """
    Currently only supporting primitive types.
    """
    if type_name == "number" or type_name == "float":
        return float
    elif type_name == "integer":
        return int
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
        raise SchemaConversionException("unrecognized type")


def is_optional_type(field: Type) -> bool:
    """Check if type is Optional."""
    return get_origin(field) is Union and type(None) in get_args(field)


JSONSchemaClass = TypeVar("JSONSchemaClass")
