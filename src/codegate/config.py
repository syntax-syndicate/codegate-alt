"""Configuration management for codegate."""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union

import yaml


class LogLevel(str, Enum):
    """Valid log levels."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"

    @classmethod
    def _missing_(cls, value: str) -> Optional["LogLevel"]:
        """Handle case-insensitive lookup of enum values."""
        try:
            # Convert to uppercase and look up directly
            return cls[value.upper()]
        except (KeyError, AttributeError):
            raise ValueError(
                f"'{value}' is not a valid LogLevel. "
                f"Valid levels are: {', '.join(level.value for level in cls)}"
            )


class LogFormat(str, Enum):
    """Valid log formats."""

    JSON = "JSON"
    TEXT = "TEXT"

    @classmethod
    def _missing_(cls, value: str) -> Optional["LogFormat"]:
        """Handle case-insensitive lookup of enum values."""
        try:
            # Convert to uppercase and look up directly
            return cls[value.upper()]
        except (KeyError, AttributeError):
            raise ValueError(
                f"'{value}' is not a valid LogFormat. "
                f"Valid formats are: {', '.join(format.value for format in cls)}"
            )


class ConfigurationError(Exception):
    """Raised when there's an error in configuration."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        # You can add additional logging or handling here if needed


@dataclass
class Config:
    """Application configuration with priority resolution."""

    port: int = 8989
    host: str = "localhost"
    log_level: LogLevel = LogLevel.INFO
    log_format: LogFormat = LogFormat.JSON

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            raise ConfigurationError("Port must be between 1 and 65535")

        if not isinstance(self.log_level, LogLevel):
            try:
                self.log_level = LogLevel(self.log_level)
            except ValueError as e:
                raise ConfigurationError(f"Invalid log level: {e}")

        if not isinstance(self.log_format, LogFormat):
            try:
                self.log_format = LogFormat(self.log_format)
            except ValueError as e:
                raise ConfigurationError(f"Invalid log format: {e}")

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "Config":
        """Load configuration from a YAML file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            Config: Configuration instance

        Raises:
            ConfigurationError: If the file cannot be read or parsed
        """
        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)

            if not isinstance(config_data, dict):
                raise ConfigurationError("Config file must contain a YAML dictionary")

            return cls(
                port=config_data.get("port", cls.port),
                host=config_data.get("host", cls.host),
                log_level=config_data.get("log_level", cls.log_level.value),
                log_format=config_data.get("log_format", cls.log_format.value),
            )
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse config file: {e}")
        except OSError as e:
            raise ConfigurationError(f"Failed to read config file: {e}")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config: Configuration instance
        """
        try:
            config = cls()

            if "CODEGATE_APP_PORT" in os.environ:
                config.port = int(os.environ["CODEGATE_APP_PORT"])
            if "CODEGATE_APP_HOST" in os.environ:
                config.host = os.environ["CODEGATE_APP_HOST"]
            if "CODEGATE_APP_LOG_LEVEL" in os.environ:
                config.log_level = LogLevel(os.environ["CODEGATE_APP_LOG_LEVEL"])
            if "CODEGATE_LOG_FORMAT" in os.environ:
                config.log_format = LogFormat(os.environ["CODEGATE_LOG_FORMAT"])

            return config
        except ValueError as e:
            raise ConfigurationError(f"Invalid environment variable value: {e}")

    @classmethod
    def load(
        cls,
        config_path: Optional[Union[str, Path]] = None,
        cli_port: Optional[int] = None,
        cli_host: Optional[str] = None,
        cli_log_level: Optional[str] = None,
        cli_log_format: Optional[str] = None,
    ) -> "Config":
        """Load configuration with priority resolution.

        Priority order (highest to lowest):
        1. CLI arguments
        2. Environment variables
        3. Config file
        4. Default values

        Args:
            config_path: Optional path to config file
            cli_port: Optional CLI port override
            cli_host: Optional CLI host override
            cli_log_level: Optional CLI log level override
            cli_log_format: Optional CLI log format override

        Returns:
            Config: Resolved configuration

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Start with defaults
        config = cls()

        # Load from config file if provided
        if config_path:
            try:
                config = cls.from_file(config_path)
            except ConfigurationError as e:
                # Log warning but continue with defaults
                import logging

                logging.warning(f"Failed to load config file: {e}")

        # Override with environment variables
        env_config = cls.from_env()
        if "CODEGATE_APP_PORT" in os.environ:
            config.port = env_config.port
        if "CODEGATE_APP_HOST" in os.environ:
            config.host = env_config.host
        if "CODEGATE_APP_LOG_LEVEL" in os.environ:
            config.log_level = env_config.log_level
        if "CODEGATE_LOG_FORMAT" in os.environ:
            config.log_format = env_config.log_format

        # Override with CLI arguments
        if cli_port is not None:
            config.port = cli_port
        if cli_host is not None:
            config.host = cli_host
        if cli_log_level is not None:
            config.log_level = LogLevel(cli_log_level)
        if cli_log_format is not None:
            config.log_format = LogFormat(cli_log_format)

        return config
