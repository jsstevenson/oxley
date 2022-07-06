"""Define miscellaneous utilities for working with Pydantic classes."""
import logging
from typing import Any, Dict, Type

from pydantic import BaseConfig
from pydantic.config import Extra

logger = logging.getLogger(__name__)


def get_configs(
    name: str, definition: Dict, allow_population_by_field_name_setting: bool
) -> Type[BaseConfig]:
    """
    Set model configs from definition attributes. This part of Pydantic gets a little
    hairy, so lots of type check suppression is needed to ensure successful
    conformity to the necessary arg structure.

    Args:
        name: class name
        definition: item definition from schema.
        allow_population_by_field_name_setting: use attribute alias in output instead of
            original name.

    Returns:
        Class based on BaseConfig with new attributes set, where necessary
    """
    if "additionalProperties" in definition:
        additional_properties = definition["additionalProperties"]
        if additional_properties is False:
            extra_value = Extra.forbid
        elif additional_properties is True:
            extra_value = Extra.allow
        else:
            logger.warning(
                f"Unrecognized additionalProperties value: {additional_properties}"
            )
            extra_value = Extra.ignore
    else:
        extra_value = Extra.ignore

    schema_extra_value = {}  # type: ignore
    if "example" in definition:

        def schema_extra_function(schema: Dict[str, Any], model: Type[name]) -> None:  # type: ignore
            """Configure schema"""
            schema["example"] = definition["example"]

        schema_extra_value = schema_extra_function  # type: ignore

    ModifiedConfig = type(
        f"{name}Config",
        (BaseConfig,),
        {
            "extra": extra_value,
            "allow_population_by_field_name": allow_population_by_field_name_setting,
            "schema_extra": schema_extra_value,
        },
    )

    return ModifiedConfig
