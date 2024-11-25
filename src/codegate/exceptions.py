"""Exceptions for codegate."""


class ConfigurationError(Exception):
    """Raised when there's an error in configuration."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
