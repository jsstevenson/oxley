import pytest
from pydantic import ValidationError

from respected_wizard.class_builder import ClassBuilder

@pytest.fixture(scope='module')
def basic_schema():
    return 'tests/data/basic_schema.json'


@pytest.fixture(scope='module')
def basic_vrs_schema():
    return 'tests/data/basic_vrs.json'


def test_basic_schema(basic_schema):
    class_builder = ClassBuilder(basic_schema)

    Point = class_builder.models[0]
    point = Point(x=2, y=3)
    assert point.x == 2
    assert point.y == 3

    with pytest.raises(ValidationError):
        assert Point(x=2)

    with pytest.raises(ValidationError):
        assert Point(x=2, y=3, z=1)


def test_basic_vrs_schema(basic_vrs_schema):
    class_builder = ClassBuilder(basic_vrs_schema)

    Number = class_builder.models[0]

    number = Number(value=5, type="Number")
    assert number.value == 5
    assert number.type == "Number"

    number = Number(value=5)
    assert number.value == 5
    assert number.type == "Number"

    with pytest.raises(ValidationError):
        assert Number(value=3, type="Float")
