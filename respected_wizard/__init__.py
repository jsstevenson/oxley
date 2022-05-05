"""Initialize module."""
import sys
import logging

from respected_wizard.class_builder import ClassBuilder


__version__ = "0.0.1"
__all__ = ["ClassBuilder"]

logging.basicConfig(
    handlers=[logging.FileHandler("respected_wizard.log"), logging.StreamHandler()]
)
