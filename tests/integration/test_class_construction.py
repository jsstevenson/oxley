"""Test model outputs from built-in example schemas."""
import pytest
from pydantic.error_wrappers import ValidationError

from oxley import ClassBuilder


@pytest.fixture(scope="module")
def example_schema_classes():
    cb = ClassBuilder("tests/data/example_schema.json")
    models = cb.build_classes()
    return {m.__name__: m for m in models}


def test_basics(example_schema_classes):
    """Run basic, high-level tests."""
    Car = example_schema_classes["Car"]
    pathfinder = Car(make="Nissan", model="Pathfinder", year=1991)
    assert pathfinder.make == "Nissan"
    assert pathfinder.model == "Pathfinder"
    assert pathfinder.year == 1991

    Garage = example_schema_classes["Garage"]
    g = Garage(car=pathfinder)
    assert g.car.make == "Nissan"
    assert g.car.model == "Pathfinder"
    assert g.car.year == 1991


def test_required_values(example_schema_classes):
    """Test `required` attribute."""
    Car = example_schema_classes["Car"]
    with pytest.raises(ValidationError) as exc_info:
        Car(make="nissan", year=1991)
    assert (
        str(exc_info.value)
        == "1 validation error for Car\nmodel\n  field required (type=value_error.missing)"  # noqa: E501
    )


def test_additional_values(example_schema_classes):
    """Test additional values allowed/ignored settings."""
    Garage = example_schema_classes["Garage"]
    with pytest.raises(ValidationError):
        Garage(**{"car": {"model": "Charger"}, "capacity": 2})

    FlexibleInt = example_schema_classes["FlexibleInt"]
    fi = FlexibleInt(value=5, other_value="30")
    assert fi.value == 5
    assert fi.other_value == "30"

    FlexibleGarage = example_schema_classes["FlexibleGarage"]
    fg = FlexibleGarage(**{"car": {"model": "Charger"}, "capacity": 2})
    assert fg.car.model == "Charger"
    assert fg.capacity == 2

    # ignore by default
    Car = example_schema_classes["Car"]
    assert Car(make="Nissan", model="Pathfinder", transmission="manual")


def test_deprecated_alert(example_schema_classes, caplog):
    """
    Check correct display of deprecation warnings in objects and properties
    """
    # test deprecated property
    caplog.clear()
    Phone = example_schema_classes["Phone"]
    Phone(number="555-9999")
    assert (
        "WARNING" not in caplog.text
        and "Property Phone.wall_mounted is deprecated" not in caplog.text
    )

    Phone(number="555-6666", wall_mounted=True)
    assert (
        "WARNING" in caplog.text
        and "Property Phone.wall_mounted is deprecated" in caplog.text
    )

    caplog.clear()
    Knight = example_schema_classes["Knight"]
    Knight(age=99)
    assert "WARNING" in caplog.text and "Class Knight is deprecated" in caplog.text

    # check no warning on oxley class construction -- delay until the deprecated class
    # itself is initialized
    caplog.clear()
    cb = ClassBuilder("tests/data/example_schema.json")
    cb.build_classes()
    assert (
        "WARNING" not in caplog.text and "Class Knight is deprecated" not in caplog.text
    )


def test_enum_property(example_schema_classes):
    """
    Check proper incorporation of enum properties.
    """
    Car = example_schema_classes["Car"]
    Car(make="Nissan", model="Pathfinder", body_style="SUV")

    with pytest.raises(ValidationError):
        Car(make="Nissan", model="Pathfinder", body_style="suv")


def test_include_descriptions(example_schema_classes):
    """
    Check for retaining descriptions for Pydantic schema output.
    """
    Car = example_schema_classes["Car"]
    assert (
        Car.schema()["properties"]["make"]["description"]
        == "The brand of the car, e.g.. Ford, Toyota, Subaru"
    )

    Knight = example_schema_classes["Knight"]
    assert (
        Knight.schema()["description"]
        == "A knight is a person granted an honorary title of knighthood by a head of state (including the Pope) or representative for service to the monarch, the church or the country, especially in a military capacity"  # noqa: E501
    )


def test_handle_leading_underscore_fields(example_schema_classes):
    """
    Check for handling properties with leading aliases in names
    """
    Record = example_schema_classes["Record"]
    cisplatin = Record(id="ncit:C376", value="cisplatin")
    assert cisplatin.id == "ncit:C376"
    assert cisplatin.schema()["properties"]["_id"]

    cellular_component = Record(**{"_id": "GO:0008372"})
    cellular_component_dict = cellular_component.dict()
    assert cellular_component_dict["_id"] == "GO:0008372"
    assert "id" not in cellular_component_dict


def test_default_value(example_schema_classes):
    """
    Check that default property values are correctly handled.
    """
    Knight = example_schema_classes["Knight"]
    knight = Knight()
    assert knight.title == "Sir Lancelot"

    knight = Knight(title="Sir Gawain")
    assert knight.title == "Sir Gawain"


def test_include_examples(example_schema_classes):
    """
    Check that examples are constructed by config objects and available in schema.
    """
    Car = example_schema_classes["Car"]
    assert Car.schema()["example"] == {
        "make": "Nissan",
        "model": "Pathfinder",
        "year": 1991,
    }


def test_http_ref(example_schema_classes):
    """Test HTTP resolution of type definitions."""
    CategoricalVariationDescriptor = example_schema_classes[
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


def test_array(example_schema_classes):
    """Test construction of classes that use arrays.
    Cases lifted from
    https://json-schema.org/understanding-json-schema/reference/array.html
    """
    ArrayTester = example_schema_classes["ArrayTester"]
    tester = ArrayTester(values_list=[1, 2, 3, 4, 5])
    assert tester.values_list == [1, 2, 3, 4, 5]
    assert ArrayTester(values_list=[3, "different", {"types": "of values"}])
    with pytest.raises(ValidationError):
        ArrayTester(values_list={"Not": "an array"})

    assert ArrayTester(numbers_list=[1, 2, 3, 4, 5])
    with pytest.raises(ValidationError):
        ArrayTester(numbers_list=[1, 2, "a", 4, 5])
    assert ArrayTester(numbers_list=[])

    assert ArrayTester(address_tuple=[1600, "Pennsylvania", "Avenue", "NW"])
    with pytest.raises(ValidationError):
        ArrayTester(address_tuple=[24, "Sussex", "Drive"])
    with pytest.raises(ValidationError):
        ArrayTester(address_tuple=["Palais de l'Élysée"])
    assert ArrayTester(address_tuple=[10, "Downing", "Street"])
    assert ArrayTester(
        address_tuple=[1600, "Pennsylvania", "Avenue", "NW", "Washington"]
    )

    assert ArrayTester(exclusive_address_tuple=[1600, "Pennsylvania", "Avenue", "NW"])
    assert ArrayTester(exclusive_address_tuple=[1600, "Pennsylvania", "Avenue"])
    with pytest.raises(ValidationError):
        ArrayTester(
            exclusive_address_tuple=[1600, "Pennsylvania", "Avenue", "NW", "Washington"]
        )

    assert ArrayTester(
        exclusive_address_tuple_string=[
            1600,
            "Pennsylvania",
            "Avenue",
            "NW",
            "Washington",
        ]
    )
    with pytest.raises(ValidationError):
        ArrayTester(
            exclusive_address_tuple_string=[1600, "Pennsylvania", "Avenue", "NW", 20500]
        )

    assert ArrayTester(contains_array=["life", "universe", "everything", 42])
    with pytest.raises(ValidationError):
        ArrayTester(contains_array=["life", "universe", "everything", "forty-two"])
    assert ArrayTester(contains_array=[1, 2, 3, 4, 5])

    with pytest.raises(ValidationError):
        ArrayTester(min_max_contains_array=["apple", "orange", 2])
    with pytest.raises(ValidationError):
        ArrayTester(min_max_contains_array=["apple", "orange", 2, 4, 8, 16])
    assert ArrayTester(min_max_contains_array=["apple", "orange", 2, 4])
    assert ArrayTester(min_max_contains_array=["apple", "orange", 2, 4, 8])

    with pytest.raises(ValidationError):
        ArrayTester(array_length=[])
    with pytest.raises(ValidationError):
        ArrayTester(array_length=[1])
    assert ArrayTester(array_length=[1, 2])
    assert ArrayTester(array_length=[1, 2, 3])
    with pytest.raises(ValidationError):
        ArrayTester(array_length=[1, 2, 3, 4])

    assert ArrayTester(uniqueness_array=[1, 2, 3, 4, 5])
    assert ArrayTester(uniqueness_array=[])
    with pytest.raises(ValidationError):
        ArrayTester(uniqueness_array=[1, 2, 3, 3, 4])

    assert ArrayTester(curie_array=["a:b", "c:d"])
    with pytest.raises(ValidationError):
        ArrayTester(curie_array=["ab", "cd"])

    assert ArrayTester(tupleNumber=["a", 10])
    with pytest.raises(ValidationError):
        ArrayTester(tupleNumber=["a", 9])

    assert ArrayTester(arrayNumber=[50, 11])
    assert ArrayTester(arrayNumber=[])
    with pytest.raises(ValidationError):
        ArrayTester(arrayNumber=[10])


def test_number(example_schema_classes):
    """Test number type properties."""
    NumberTester = example_schema_classes["NumberTester"]
    assert NumberTester(integer=42)
    assert NumberTester(integer=-1)
    with pytest.raises(ValidationError):
        NumberTester(integer=3.14159)

    assert NumberTester(number=42)
    assert NumberTester(number=-1)
    assert NumberTester(number=5.0)
    assert NumberTester(number=2.999999e8)
    with pytest.raises(ValidationError):
        NumberTester(number="42")

    assert NumberTester(multipleOf=0)
    assert NumberTester(multipleOf=10)
    assert NumberTester(multipleOf=10000)
    with pytest.raises(ValidationError):
        NumberTester(multipleOf=23)

    assert NumberTester(range=0)
    assert NumberTester(range=10)
    assert NumberTester(range=99)
    with pytest.raises(ValidationError):
        NumberTester(range=-1)
    with pytest.raises(ValidationError):
        NumberTester(range=100)
    with pytest.raises(ValidationError):
        NumberTester(range=101)

    BigNumber = example_schema_classes["BigNumber"]
    assert BigNumber(1001)
    with pytest.raises(ValidationError):
        BigNumber(999)
