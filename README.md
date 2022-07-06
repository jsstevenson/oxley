<h1 align="center">
    Oxley: Pydantic classes from JSON schema
</h1>

## What, why

**Oxley** generates [Pydantic](https://github.com/samuelcolvin/pydantic) classes at runtime from user-provided JSON schema documents. Heavily indebted to packages like [Python-JSONschema-Objects](https://github.com/cwacek/python-jsonschema-objects), Oxley enables data validation pipelines to function dynamically, and with the help of Pydantic, interface directly with popular web frameworks such as [FastAPI](https://github.com/tiangolo/fastapi).

## Quick start

Install from PIP:

```shell
python3 -m pip install oxley
```

Provide a schema and construct classes:

``` python
>>> from oxley import ClassBuilder
>>> schema_path = "tests/data/basic_schema.json"
>>> cb = ClassBuilder(schema_path)
>>> PointHolder, Point, Car, Friend, Knight = cb.build_classes()  # fill in here
```

The resulting objects are functioning Pydantic classes, providing features like runtime data validation and matching schema output.

``` python
# fill in data validation examples here
```

## Development

Clone and install dev and test dependencies:

``` shell
git clone https://github.com/jsstevenson/oxley
cd oxley
# make virtual environment of your choosing
python3 -m pip install ".[dev,test]"
```

Install pre-commit hooks:

``` shell
pre-commit install
```

Run tests with tox:

```
tox
```
