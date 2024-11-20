"""Codegate - A configurable service gateway."""

from importlib import metadata

try:
    __version__ = metadata.version("codegate")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"

from .config import Config, ConfigurationError
from .logging import setup_logging

__all__ = ["Config", "ConfigurationError", "setup_logging"]
