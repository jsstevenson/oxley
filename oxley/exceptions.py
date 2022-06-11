"""Provide package-wide Exceptions."""


class UnsupportedSchemaException(Exception):
    """Raise error where schema doesn't use one of the package-supported JSONSchema
    versions."""

    pass


class InvalidReferenceException(Exception):
    """Raise error when reference values can't be parsed."""

    pass


class SchemaConversionException(Exception):
    """Raise errors where valid JSONSchema elements may not fit into the Python type or
    object systems."""

    pass
