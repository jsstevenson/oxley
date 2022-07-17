"""Test validator constructor methods."""
import pytest

from oxley.validators import (
    create_array_contains_validator,
    create_array_length_validator,
    create_array_unique_validator,
    create_tuple_validator,
)


def test_tuple_validator():
    """Test `create_tuple_validator`"""
    validate_tuple = create_tuple_validator(
        {
            "type": "array",
            "prefixItems": [
                {"type": "number"},
                {"enum": [5, 10, 15]},
                {"type": "boolean"},
                {"type": "string"},
            ],
        }
    )
    assert validate_tuple(None, [10, 10, False, "yes"])
    assert validate_tuple(None, [10])
    assert validate_tuple(None, [5, 5, True, "no", "extra", 100])
    assert validate_tuple(None, []) == []
    with pytest.raises(ValueError):
        validate_tuple(None, ["Palais de l'Élysée"])
    with pytest.raises(ValueError):
        validate_tuple(None, [24, 14, False, "Drive"])

    validate_tuple = create_tuple_validator({"type": "array", "prefixItems": []})
    assert validate_tuple(None, "yes")

    validate_tuple = create_tuple_validator(
        {
            "type": "array",
            "prefixItems": [{"type": "string"}, {"type": "number"}],
            "items": False,
        }
    )
    assert validate_tuple(None, ["1", 1])
    with pytest.raises(ValueError):
        validate_tuple(None, ["a", 1, "b"])

    validate_tuple = create_tuple_validator(
        {
            "type": "array",
            "prefixItems": [{"type": "string"}, {"type": "number"}],
            "items": {"type": "string"},
        }
    )
    assert validate_tuple(None, ["1", 1, "1"])
    with pytest.raises(ValueError):
        validate_tuple(None, ["1", 1, 1])

    validate_tuple = create_tuple_validator(
        {
            "type": "array",
            "prefixItems": [{"type": "string"}, {"type": "number"}],
            "items": {"enum": [1, 10, 100]},
        }
    )
    assert validate_tuple(None, ["1", 1, 1])
    with pytest.raises(ValueError):
        validate_tuple(None, ["1", 1, "1"])


def test_array_contains_validator():
    """Test `create_array_contains_validator`"""
    array_contains_validator = create_array_contains_validator(
        {"type": "string"}, None, 3
    )
    assert array_contains_validator(None, [1, "1", 1, 2, 3])
    assert array_contains_validator(None, ["a"])
    with pytest.raises(ValueError):
        array_contains_validator(None, [1])
    with pytest.raises(ValueError):
        array_contains_validator(None, [1, 1, 1, "a", "b", "c", "d"])

    array_contains_validator = create_array_contains_validator({"type": "number"}, 2, 3)
    assert array_contains_validator(None, ["a", 1, 1])
    with pytest.raises(ValueError):
        array_contains_validator(None, ["a", 99])
    with pytest.raises(ValueError):
        array_contains_validator(None, ["zzz", 9, 99, 999, 9999])


def test_array_length_validator():
    """Test `create_array_length_validator`"""
    array_length_validator = create_array_length_validator(2, None)
    assert array_length_validator(None, [1, 2])
    assert array_length_validator(None, list(range(99)))
    with pytest.raises(ValueError):
        array_length_validator(None, [1])


def test_array_unique_validator():
    """Test `create_array_unique_validator`."""
    validate_array_unique = create_array_unique_validator()
    assert validate_array_unique(None, [1, 2, 3, 4, 5])
    assert validate_array_unique(None, ["a", 2, "2"])
    assert validate_array_unique(None, [False, 0])
    assert validate_array_unique(None, []) == []
    with pytest.raises(ValueError):
        validate_array_unique(None, ["a", 2, "b", "b"])
