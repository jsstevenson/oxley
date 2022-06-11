import pytest
from pydantic import ValidationError

from oxley.class_builder import ClassBuilder


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


@pytest.fixture(scope="module")
def basic_vrsatile_models():
    """Provide basic VRSATILE schema fixture."""
    class_builder = ClassBuilder("tests/data/basic_vrsatile.json")
    models = class_builder.build_classes()
    return {m.__name__: m for m in models}


def test_basic_schema(basic_schema_models):
    Point = basic_schema_models["Point"]
    point = Point(x=2, y=3)
    assert point.x == 2
    assert point.y == 3

    with pytest.raises(ValidationError):
        assert Point(x=2)

    with pytest.raises(ValidationError):
        assert Point(x=2, y=3, z=1)

    # test forward refs
    PointHolder = basic_schema_models["PointHolder"]
    point_holder = PointHolder(point=Point(x=2, y=3))
    assert point_holder.point.x == 2
    assert point_holder.point.y == 3

    # test optional
    Car = basic_schema_models["Car"]
    car = Car(make="Toyota", model="RAV4")
    assert car.make == "Toyota"
    assert car.model == "RAV4"
    assert car.trim is None

    # test enum
    Friend = basic_schema_models["Friend"]
    franklin = Friend(name="Franklin")
    assert franklin.name == "Franklin"

    with pytest.raises(ValidationError):
        Friend(name="Francois")


def test_deprecated_warning(caplog):
    class_builder = ClassBuilder("tests/data/basic_schema.json")
    class_builder.build_classes()
    assert "WARNING" in caplog.text and "Class Car is deprecated" in caplog.text


def test_basic_vrs_schema(basic_vrs_models):
    Number = basic_vrs_models["Number"]
    number = Number(value=5, type="Number")
    assert number.value == 5
    assert number.type == "Number"

    number = Number(value=5)
    assert number.value == 5
    assert number.type == "Number"

    with pytest.raises(ValidationError):
        assert Number(value=3, type="Float")

    # test pattern checks and single derivative types/not objects
    CURIE = basic_vrs_models["CURIE"]
    curie = CURIE("chembl:CHEMBL11359")
    assert curie == "chembl:CHEMBL11359"

    Text = basic_vrs_models["Text"]
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


def test_examples(basic_vrs_models):
    """
    Check that examples are constructed by config objects and available in schema.
    """
    CytobandInterval = basic_vrs_models["CytobandInterval"]
    schema = CytobandInterval.schema()
    assert "example" in schema
    assert schema["example"] == {
        "type": "CytobandInterval",
        "start": "q22.2",
        "end": "q22.3",
    }


def test_http_ref(basic_vrsatile_models):
    """Test HTTP resolution of type definitions."""
    CategoricalVariationDescriptor = basic_vrsatile_models[
        "CategoricalVariationDescriptor"
    ]
    cvd = CategoricalVariationDescriptor(
        id="clinvar:vcv001",
        type="VariationDescriptor",
        xrefs=["oncokb:999"],
    )
    assert cvd.id == "clinvar:vcv001"
    assert cvd.type == "VariationDescriptor"
    assert set(cvd.xrefs) == {"oncokb:999"}
