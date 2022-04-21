import pytest
from pydantic import ValidationError

from respected_wizard.class_builder import ClassBuilder


@pytest.fixture(scope="module")
def basic_schema():
    return "tests/data/basic_schema.json"


@pytest.fixture(scope="module")
def basic_vrs_schema():
    return "tests/data/basic_vrs.json"


def test_basic_schema(basic_schema):
    class_builder = ClassBuilder(basic_schema)

    Point = class_builder.models[1]
    point = Point(x=2, y=3)
    assert point.x == 2
    assert point.y == 3

    with pytest.raises(ValidationError):
        assert Point(x=2)

    with pytest.raises(ValidationError):
        assert Point(x=2, y=3, z=1)

    # test forward refs
    PointHolder = class_builder.models[0]
    point_holder = PointHolder(point=Point(x=2, y=3))
    assert point_holder.point.x == 2
    assert point_holder.point.y == 3

    # test optional
    Car = class_builder.models[2]
    car = Car(make="Toyota", model="RAV4")
    assert car.make == "Toyota"
    assert car.model == "RAV4"
    assert car.trim is None


def test_basic_vrs_schema(basic_vrs_schema):
    class_builder = ClassBuilder(basic_vrs_schema)

    Number, CURIE, Text = class_builder.models

    number = Number(value=5, type="Number")
    assert number.value == 5
    assert number.type == "Number"

    number = Number(value=5)
    assert number.value == 5
    assert number.type == "Number"

    with pytest.raises(ValidationError):
        assert Number(value=3, type="Float")

    # test pattern checks and single derivative types/not objects
    curie = CURIE("chembl:CHEMBL11359")
    assert curie == "chembl:CHEMBL11359"
    text = Text(id=curie, definition="Some words about cisplatin idk")
    assert text.id == curie
    assert text.definition == "Some words about cisplatin idk"
    assert Text(definition="more words")  # id optional

    with pytest.raises(ValidationError):
        assert Text(id="CHEMBL11359", definition="Cisplatin")
