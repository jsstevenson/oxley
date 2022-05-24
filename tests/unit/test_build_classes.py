import pytest
from pydantic import ValidationError

from respected_wizard.class_builder import ClassBuilder


@pytest.fixture(scope="module")
def basic_schema():
    return "tests/data/basic_schema.json"


@pytest.fixture(scope="module")
def basic_vrs_schema():
    return "tests/data/basic_vrs.json"


def test_basic_schema(basic_schema, caplog):
    class_builder = ClassBuilder(basic_schema)
    models = class_builder.build_classes()

    Point = models[1]
    point = Point(x=2, y=3)
    assert point.x == 2
    assert point.y == 3

    with pytest.raises(ValidationError):
        assert Point(x=2)

    with pytest.raises(ValidationError):
        assert Point(x=2, y=3, z=1)

    # test forward refs
    PointHolder = models[0]
    point_holder = PointHolder(point=Point(x=2, y=3))
    assert point_holder.point.x == 2
    assert point_holder.point.y == 3

    # test optional
    Car = models[2]
    car = Car(make="Toyota", model="RAV4")
    assert car.make == "Toyota"
    assert car.model == "RAV4"
    assert car.trim is None

    # test deprecated warning
    assert "WARNING" in caplog.text and "Class Car is deprecated" in caplog.text

    # test enum
    Friend = models[3]
    franklin = Friend(name="Franklin")
    assert franklin.name == "Franklin"

    with pytest.raises(ValidationError):
        Friend(name="Francois")


def test_basic_vrs_schema(basic_vrs_schema):
    class_builder = ClassBuilder(basic_vrs_schema)
    models = class_builder.build_classes()

    Number, CURIE, Text = models

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
