"""Test typing module."""
from typing import Optional, Union

import pytest

from oxley.exceptions import SchemaConversionException
from oxley.types import build_enum, is_optional_type, resolve_type


def test_resolve_type():
    """Test resolve_type function."""
    assert resolve_type("string") == str
    assert resolve_type("number") == float
    assert resolve_type("boolean") == bool
    assert resolve_type("array") == list
    assert resolve_type("object") == dict
    assert resolve_type("null") is None
    assert resolve_type(["string", "number"]) == Union[str, float]
    assert resolve_type(["object"]) == dict

    with pytest.raises(TypeError) as exc_info:
        resolve_type([])
    assert str(exc_info.value) == "Cannot take a Union of no types."

    with pytest.raises(SchemaConversionException) as exc_info:
        resolve_type("int")
    assert str(exc_info.value) == "unrecognized type"

    with pytest.raises(SchemaConversionException) as exc_info:
        resolve_type(["array", "int"])
    assert str(exc_info.value) == "unrecognized type"


def test_is_optional_type():
    """Test is_optional_type function."""
    assert is_optional_type(Optional[int])
    assert not is_optional_type(Optional)
    assert is_optional_type(Union[str, int, None])
    assert not is_optional_type(Union[str, int])
    assert not is_optional_type(str)


def test_build_enum():
    """Test build_enum function."""
    RelativeCopyClass = build_enum(
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
    Comparator = build_enum(
        "comparator",
        {
            "type": "string",
            "enum": ["<=", ">="],
            "description": 'MUST be one of "<=" or ">=", indicating which direction the range is indefinite',  # noqa: E501
        },
    )
    assert Comparator.__.value == "<="  # type: ignore
    assert Comparator.___A.value == ">="  # type: ignore

    with pytest.raises(SchemaConversionException) as exc_info:
        build_enum("multiple_value_types", {"enum": [1, "a"]})
    assert str(exc_info.value) == "Enum values must all be the same type"

    with pytest.raises(SchemaConversionException) as exc_info:
        build_enum(
            "non_primitive_types", {"type": "object", "enum": [{"a": 1}, {"b": 2}]}
        )

    assert (
        str(exc_info.value)
        == "Unable to construct enum from type <class 'dict'>. Must be one of {`str`, `int`, `float`, `bool`}"  # noqa: E501
    )  # noqa: E501
