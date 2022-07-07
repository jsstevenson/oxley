<h1 align="center">
    Oxley: Pydantic classes from JSON schema
</h1>

**Oxley** generates [Pydantic](https://github.com/samuelcolvin/pydantic) classes at runtime from user-provided JSON schema documents. Heavily indebted to packages like [Python-JSONschema-Objects](https://github.com/cwacek/python-jsonschema-objects), Oxley enables data validation pipelines to function dynamically, and with the help of Pydantic, interface directly with popular web frameworks such as [FastAPI](https://github.com/tiangolo/fastapi) and [Starlite](https://github.com/starlite-api/starlite).

## Quick start

Install from PIP:

```shell
python3 -m pip install oxley
```

Given a simple JSONschema document:

```json
{
  "$id": "https://github.com/jsstevenson/oxley",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "$defs": {
    "User": {
      "type": "object",
      "properties": {
        "username": {"type": "string"},
        "user_id": {"type": "number"}
      },
      "required": ["username", "user_id"]
    },
    "Post": {
      "type": "object",
      "properties": {
        "author": {"$ref": "#/$defs/User"},
        "content": {"type": "string"},
        "allow_responses": {"type": "boolean"}
      },
      "required": ["author", "content"]
    }
  }
}
```

Provide a schema and construct classes:

``` python
from oxley import ClassBuilder
schema_path = "path/to/my_jsonschema_document.json"
cb = ClassBuilder(schema_path)
User, Post = cb.build_classes()
```

The resulting objects are functioning Pydantic classes, providing features like runtime data validation and matching schema output.

``` python
dril = User(username="dril", user_id=99)
post = Post(author=dril, content="should i learn Letters first?  or choose the path of Numbers? a queston every baby must ask it self")
another_post = Post(author=dril)  # raises pydantic.ValidationError
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
