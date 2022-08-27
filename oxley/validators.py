"""Provide helper functions for validator construction."""
import re
from typing import Any, Callable, Dict, Optional, get_args

from pydantic import validator

from oxley.exceptions import SchemaParseException
from oxley.types import convert_type_name, is_number_type, is_union_type


def create_tuple_validator(prop_attrs: Dict) -> Callable:
    """
    Construct validator function for tuple-like arrays. `validate_slot` docstring
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
    type_definition: Dict,
    min_contains: Optional[int],
    max_contains: Optional[int],
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
        contains_count = sum([validate_slot(v_i, type_definition) for v_i in v])
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


def validate_slot(value: Any, type_definition: Optional[Dict[str, Any]]) -> bool:
    """
    Helper function for validators to use in tuple-like arrays.
    For example, JSONschema uses the "prefixItems" attribute to impose requirements on specific slots
    within arrays (i.e., as if they're typed tuples). Pydantic doesn't play well with some edge
    features of this setup, so we use validator functions to perform checks manually rather than
    coming up with tricky type annotations.

    Args:
        value: the individual value to check
        type_definition: definition to check against

    Return:
        true if value meets the type_definition, false otherwise

    Raises:
        SchemaParseException: if expected type definition styles are missing
    """
    if type_definition is None:
        raise SchemaParseException(
            f"Could not provide slot type checks given type definition {type_definition}"
        )
    else:
        if "type" in type_definition:
            # type checks
            defined_type = convert_type_name(type_definition["type"])
            if defined_type is None:
                if value is not None:
                    return False
            elif hasattr(defined_type, "strict") and getattr(defined_type, "strict"):
                try:
                    defined_type(value)  # type: ignore
                except ValueError:
                    return False
            elif is_union_type(defined_type):
                for subtype in get_args(defined_type):
                    if hasattr(subtype, "strict") and getattr(subtype, "strict"):
                        try:
                            subtype(value)  # type: ignore
                        except ValueError:
                            return False
            elif not isinstance(value, defined_type):  # type: ignore
                return False

            # custom validations
            if defined_type is not None:
                if is_number_type(defined_type):
                    validators = get_number_validators("", type_definition)
                    for validator_fn in validators.values():
                        try:
                            validator_fn(None, value)
                        except ValueError:
                            return False
        if "enum" in type_definition:
            if value not in type_definition["enum"]:
                return False
    return True


def create_number_multiple_validator(num: float) -> Callable:
    """
    Construct number multipleOf validator.

    The JSONschema specs suggest `num` can probably be a float. I'm a little uneasy
    about the reliability of multiple_of checks involving non-integers, but the spec
    is the spec.

    Args:
        num: value to check if multiple of

    Return:
        function to pass to Pydantic validator constructor
    """

    def validate_number_multiple_of(cls, v):
        if v % num != 0:
            raise ValueError
        return v

    return validate_number_multiple_of


def get_number_validators(prop_name: str, prop_attrs: Dict) -> Dict[str, Callable]:
    """
    Get base validator functions for number property/type. Direct use in the Pydantic
    validation phase requires a wrapper function that calls `pydantic.validator()` on
    them.

    Args:
        prop_name: field name of property
        prop_attrs: numeric property attributes

    Return:
        Validator names mapped to functions
    """
    validators = {}
    if "multipleOf" in prop_attrs:
        validate_multiple = create_number_multiple_validator(prop_attrs["multipleOf"])
        validators[f"validate_{prop_name}_multipleOf"] = validate_multiple
    minimum = prop_attrs.get("minimum")
    exclusive_minimum = prop_attrs.get("exclusiveMinimum")
    maximum = prop_attrs.get("maximum")
    exclusive_maximum = prop_attrs.get("exclusiveMaximum")
    if any([minimum, exclusive_minimum, maximum, exclusive_maximum]):
        validate_range = create_number_range_validator(
            minimum, exclusive_minimum, maximum, exclusive_maximum
        )
        validators[f"validate_{prop_name}_range"] = validate_range
    return validators


def get_number_class_validators(
    prop_name: str, prop_attrs: Dict
) -> Dict[str, Callable]:
    """
    Get validator class methods to be used in actual Pydantic classes.

    Args:
        prop_name: field name of property
        prop_attrs: numeric property attributes

    Return:
        Validator names mapped to validator class methods
    """
    validator_functions = get_number_validators(prop_name, prop_attrs)
    return {
        fn_name: validator(prop_name, allow_reuse=True)(fn)
        for fn_name, fn in validator_functions.items()
    }  # type: ignore


def create_number_range_validator(
    minimum: Optional[float],
    exclusiveMinimum: Optional[float],
    maximum: Optional[float],
    exclusiveMaximum: Optional[float],
) -> Callable:
    """
    Construct number range validator.

    As with the multipleOf validator, checking with and against floats feels a little dire.
    It's likely legal to make this validation impossible, but no check is performed
    against that here.

    Args:
        minimum: number must be >=
        exclusiveMinimum: number must be >
        maximum: number must be <=
        exclusiveMaximum: number must be <

    Return:
        function to pass to Pydantic validator constructor
    """

    def validate_number_range(cls, v):
        if minimum is not None and v < minimum:
            raise ValueError
        if exclusiveMinimum is not None and v <= exclusiveMinimum:
            raise ValueError
        if maximum is not None and v > maximum:
            raise ValueError
        if exclusiveMaximum is not None and v >= exclusiveMaximum:
            raise ValueError
        return v

    return validate_number_range


def create_string_regex_validator(pattern: str) -> Callable:
    """
    Construct string regex pattern validator.

    Args:
        pattern: raw string to be converted into regex pattern

    Return:
        function to pass to Pydantic validator constructor
    """
    pattern_re = re.compile(pattern)

    def validate_pattern(cls, v):
        m = re.match(pattern_re, v)
        if not m:
            raise ValueError("provided value doesn't match pattern")
        return cls(v)

    return validate_pattern
