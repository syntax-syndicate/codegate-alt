"""Codegate - A configurable service gateway."""

import logging as python_logging

from .config import Config, LogFormat, LogLevel
from .exceptions import ConfigurationError
from .logging import setup_logging

__version__ = "0.1.0"
__description__ = "A configurable service gateway"

__all__ = ["Config", "ConfigurationError", "LogFormat", "LogLevel", "setup_logging"]

# Set up null handler to avoid "No handler found" warnings.
# See https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
python_logging.getLogger(__name__).addHandler(python_logging.NullHandler())
