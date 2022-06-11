"""Initialize module."""
import logging
import sys

from .class_builder import ClassBuilder
from .version import __version__

__all__ = ["ClassBuilder"]

logging.basicConfig(
    handlers=[logging.FileHandler("oxley.log"), logging.StreamHandler()]
)
