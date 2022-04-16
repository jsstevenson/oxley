import pytest
from pydantic import ValidationError

from respected_wizard.class_builder import ClassBuilder

@pytest.fixture(scope='module')
def basic_schema():
    return 'tests/data/basic_schema.json'


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
