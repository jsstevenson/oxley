"""Test core schema builder module."""
import pytest

from oxley.class_builder import ClassBuilder


def test_build_primitive_class():
    cb = ClassBuilder("tests/data/example_schema.json")
    cb._build_primitive_class(
        "PhoneNumber",
        {"type": "string", "pattern": "^\\d\\d\\d-\\d\\d\\d-\\d\\d\\d\\d$"},
    )
    PhoneNumber = cb.local_ns["PhoneNumber"]
    assert str(PhoneNumber("253-555-9999")) == "253-555-9999"
    with pytest.raises(ValueError):
        next(PhoneNumber.__get_validators__())("253-555-999")
