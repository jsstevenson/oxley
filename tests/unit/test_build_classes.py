import pytest
from pydantic import ValidationError

from respected_wizard.class_builder import ClassBuilder


@pytest.fixture(scope="module")
def basic_schema():
    return "tests/data/basic_schema.json"


@pytest.fixture(scope="module")
def basic_vrs_schema():
    return "tests/data/basic_vrs.json"


@pytest.fixture(scope="function")
def basic_schema_models():
    class_builder = ClassBuilder("tests/data/basic_schema.json")
    models = class_builder.build_classes()
    return {m.__name__: m for m in models}


@pytest.fixture(scope="function")
def basic_vrs_models():
    class_builder = ClassBuilder("tests/data/basic_vrs.json")
    models = class_builder.build_classes()
    return {m.__name__: m for m in models}


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

    Number, CURIE, Text, _ = models

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

    # check for descriptions in schema output
    number_schema = Number.schema()
    assert number_schema["description"] == "A simple integer value as a VRS class."
    assert number_schema["properties"]["type"]["description"] == 'MUST be "Number"'


def test_handle_leading_underscore_fields(basic_vrs_models):
    """
    Check for handling properties with leading aliases in names
    """
    Haplotype = basic_vrs_models["Haplotype"]
    haplotype = Haplotype(id="gml:a_haplotype", type="Haplotype")
    assert haplotype.id == "gml:a_haplotype"
    assert haplotype.schema()["properties"]["_id"]

    haplotype = Haplotype(**{"_id": "sdfjk:haplotype"})
    haplotype_dict = haplotype.dict()
    assert haplotype_dict["_id"] == "sdfjk:haplotype"
    assert "id" not in haplotype_dict


def test_default_value(basic_schema_models):
    """
    Check that default property values are correctly handled.
    """
    Knight = basic_schema_models["Knight"]
    k = Knight(age=23)
    assert k.age == 23
    assert k.title == "Sir Lancelot"

    k = Knight(age=50, title="Sir Davos")
    assert k.age == 50
    assert k.title == "Sir Davos"
