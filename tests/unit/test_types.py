"""Test typing module."""
from typing import Optional, Union

import pytest
from pydantic import StrictFloat, StrictInt

from oxley.exceptions import SchemaConversionException
from oxley.types import (
    convert_type_name,
    get_enum_type,
    is_number_type,
    is_optional_type,
)


def test_convert_type_name():
    """Test convert_type_name function."""
    assert convert_type_name("string") == str
    assert convert_type_name("number") == Union[StrictFloat, StrictInt]
    assert convert_type_name("boolean") == bool
    assert convert_type_name("array") == list
    assert convert_type_name("object") == dict
    assert convert_type_name("null") == None
    assert (
        convert_type_name(["string", "number"])
        == Union[str, Union[StrictFloat, StrictInt]]
    )
    assert convert_type_name(["object"]) == dict

    with pytest.raises(TypeError) as exc_info:
        convert_type_name([])
    assert str(exc_info.value) == "Cannot take a Union of no types."

    with pytest.raises(SchemaConversionException) as exc_info:
        convert_type_name("int")
    assert str(exc_info.value) == "unrecognized type"

    with pytest.raises(SchemaConversionException) as exc_info:
        convert_type_name(["array", "int"])
    assert str(exc_info.value) == "unrecognized type"


def test_is_optional_type():
    """Test is_optional_type function."""
    assert is_optional_type(Optional[int])
    assert not is_optional_type(Optional)
    assert is_optional_type(Union[str, int, None])
    assert not is_optional_type(Union[str, int])
    assert not is_optional_type(str)


def test_is_number_type():
    """Test is_number_type function."""
    assert is_number_type(int)
    assert is_number_type(float)
    assert is_number_type(Union[int, float])
    assert not is_number_type(Union[int, str])
    assert is_number_type(StrictInt)
    assert is_number_type(StrictFloat)
    assert is_number_type(Union[StrictInt, StrictFloat])


def test_get_enum_type():
    """Test get_enum_type function."""
    RelativeCopyClass = get_enum_type(
        "relative_copy_class",
        {
            "type": "string",
            "enum": [
                "complete loss",
                "partial loss",
                "copy neutral",
                "low-level gain",
                "high-level gain",
            ],
        },
    )
    assert RelativeCopyClass.COMPLETE_LOSS.value == "complete loss"  # type: ignore
    assert RelativeCopyClass.HIGH_LEVEL_GAIN.value == "high-level gain"  # type: ignore

    # test messed up enumerable names
    Comparator = get_enum_type(
        "comparator",
        {
            "type": "string",
            "enum": ["<=", ">="],
            "description": 'MUST be one of "<=" or ">=", indicating which direction the range is indefinite',
        },
    )
    assert Comparator.__.value == "<="  # type: ignore
    assert Comparator.___A.value == ">="  # type: ignore

    with pytest.raises(SchemaConversionException) as exc_info:
        get_enum_type("multiple_value_types", {"enum": [1, "a"]})
    assert str(exc_info.value) == "Enum values must all be the same type"

    with pytest.raises(SchemaConversionException) as exc_info:
        get_enum_type(
            "non_primitive_types", {"type": "object", "enum": [{"a": 1}, {"b": 2}]}
        )

    assert (
        str(exc_info.value)
        == "Unable to construct enum from type <class 'dict'>. Must be one of {`str`, `int`, `float`, `bool`}"
    )  # noqa: E501
