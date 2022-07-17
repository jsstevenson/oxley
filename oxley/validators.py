"""Provide helper functions for validator construction."""
from typing import Any, Callable, Dict, Optional

from .exceptions import SchemaParseException
from .types import resolve_type


def validate_slot(value: Any, type_definition: Dict) -> bool:
    """
    Helper function for validators to use in tuple-like arrays.
    JSONschema uses the "prefixItems" attribute to impose requirements on specific slots
    within arrays (i.e., as if they're typed tuples). Pydantic doesn't play well with
    some edge features of this setup, so we use validator functions to perform checks
    manually rather than coming up with tricky type annotations.

    Currently only able to handle type definitions using primitive values or inline
    enum declarations.

    Args:
        value: the individual value to check
        type_definition: definition to check against

    Return:
        true if value meets the type_definition, false otherwise

    Raises:
        SchemaParseException: if expected type definition styles are missing
    """
    if "type" in type_definition:
        type_definition_type = type_definition["type"]
        # resolve_type maps "number" -> float to be inclusive,
        # so we need a special check for ints
        if type_definition_type == "number" and isinstance(value, int):
            return True
        return isinstance(value, resolve_type(type_definition["type"]))  # type: ignore
    if "enum" in type_definition:
        return value in type_definition["enum"]
    raise SchemaParseException(
        f"Unknown tuple type definition format: {type_definition}"
    )


def create_tuple_validator(prop_attrs: Dict) -> Callable:
    """
    Construct validator function for tuple-like arrays. `types.validate_slot` docstring
    has more backstory re: necessity of validators for tuples.

    Args:
        prop_attrs: definition of the tuple (really array) property

    Return:
        function to pass to pydantic validator constructor
    """

    def validate_tuple(cls, v):
        definition_length = len(prop_attrs["prefixItems"])
        for i, value in enumerate(v[:definition_length]):
            if not validate_slot(value, prop_attrs["prefixItems"][i]):
                raise ValueError
        if "items" in prop_attrs:
            if prop_attrs["items"] is False:
                if len(v) > definition_length:
                    raise ValueError
            else:
                for value in v[len(prop_attrs["prefixItems"]) :]:
                    if not validate_slot(value, prop_attrs["items"]):
                        raise ValueError
        return v

    return validate_tuple


def create_array_contains_validator(
    contains_type: Dict, min_contains: Optional[int], max_contains: Optional[int]
) -> Callable:
    """
    Construct validator function for `contains` keyword in array validation.

    Args:
        type_definition: should be the value (an object) of the `contains` property
            in the array definition.
        min_contains: minimum number of instances expected
        max_contains: maximum number of instances expected

    Return:
        function to pass to Pydantic validator constructor
    """

    def validate_array_contains(cls, v):
        contains_count = sum([validate_slot(v_i, contains_type) for v_i in v])
        if (
            min_contains is not None and contains_count < min_contains
        ) or contains_count < 1:
            raise ValueError
        if max_contains is not None and contains_count > max_contains:
            raise ValueError
        return v

    return validate_array_contains


def create_array_length_validator(
    min_items: Optional[int], max_items: Optional[int]
) -> Callable:
    """
    Construct validator function for `minItems`/`maxItems` array properties

    Args:
        min_items: minimum number of array items
        max_items: max number of array items

    Return:
        function to pass to Pydantic validator constructor
    """

    def validate_array_length(cls, v):
        array_length = len(v)
        if min_items is not None and array_length < min_items:
            raise ValueError
        if max_items is not None and array_length > max_items:
            raise ValueError
        return v

    return validate_array_length


def create_array_unique_validator() -> Callable:
    """
    Construct array uniqueness validator.

    Uses a very ugly o(n^2) check because something more direct like set() will check
    duck type-y equivalences, so that eg `[0, False]` will raise a ValueError

    It's not strictly necessary to wrap this function in a `create` function because
    it doesn't need to hoist any scoped argument variables, but it's done here to be
    consistent with the other functions in this module.

    Return:
        function to pass to Pydantic validator constructor.
    """

    def validate_array_unique(cls, v):
        for i, v_i in enumerate(v):
            for j, v_j in enumerate(v):
                if i != j and v_i == v_j and type(v_i) == type(v_j):
                    raise ValueError
        return v

    return validate_array_unique
