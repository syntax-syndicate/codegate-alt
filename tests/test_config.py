"""Tests for configuration management."""

import os
from pathlib import Path

import pytest
import yaml

from codegate.config import Config, ConfigurationError, LogFormat, LogLevel


def test_default_config(default_config: Config) -> None:
    """Test default configuration values."""
    assert default_config.port == 8989
    assert default_config.host == "localhost"
    assert default_config.log_level == LogLevel.INFO
    assert default_config.log_format == LogFormat.JSON


def test_config_from_file(temp_config_file: Path) -> None:
    """Test loading configuration from file."""
    config = Config.from_file(temp_config_file)
    assert config.port == 8989
    assert config.host == "localhost"
    assert config.log_level == LogLevel.DEBUG
    assert config.log_format == LogFormat.JSON


def test_config_from_invalid_file(tmp_path: Path) -> None:
    """Test loading configuration from invalid file."""
    invalid_file = tmp_path / "invalid.yaml"
    with open(invalid_file, "w") as f:
        f.write("invalid: yaml: content")

    with pytest.raises(ConfigurationError):
        Config.from_file(invalid_file)


def test_config_from_nonexistent_file() -> None:
    """Test loading configuration from nonexistent file."""
    with pytest.raises(ConfigurationError):
        Config.from_file("nonexistent.yaml")


def test_config_from_env(env_vars: None) -> None:
    """Test loading configuration from environment variables."""
    config = Config.from_env()
    assert config.port == 8989
    assert config.host == "localhost"
    assert config.log_level == LogLevel.WARNING
    assert config.log_format == LogFormat.TEXT


def test_config_priority_resolution(temp_config_file: Path, env_vars: None) -> None:
    """Test configuration priority resolution."""
    # CLI args should override everything
    config = Config.load(
        config_path=temp_config_file,
        cli_port=8080,
        cli_host="example.com",
        cli_log_level="WARNING",
        cli_log_format="TEXT",
    )
    assert config.port == 8080
    assert config.host == "example.com"
    assert config.log_level == LogLevel.WARNING
    assert config.log_format == LogFormat.TEXT

    # Env vars should override config file
    config = Config.load(config_path=temp_config_file)
    assert config.port == 8989  # from env
    assert config.host == "localhost"  # from env
    assert config.log_level == LogLevel.WARNING  # from env
    assert config.log_format == LogFormat.TEXT  # from env

    # Config file should override defaults
    os.environ.clear()  # Remove env vars
    config = Config.load(config_path=temp_config_file)
    assert config.port == 8989  # from file
    assert config.host == "localhost"  # from file
    assert config.log_level == LogLevel.DEBUG  # from file
    assert config.log_format == LogFormat.JSON  # from file


def test_invalid_log_level() -> None:
    """Test handling of invalid log level."""
    with pytest.raises(ConfigurationError):
        Config(log_level="INVALID")


def test_invalid_log_format() -> None:
    """Test handling of invalid log format."""
    with pytest.raises(ConfigurationError):
        Config(log_format="INVALID")


def test_invalid_port() -> None:
    """Test handling of invalid port number."""
    with pytest.raises(ConfigurationError):
        Config(port=0)
    with pytest.raises(ConfigurationError):
        Config(port=65536)


def test_log_format_case_insensitive(tmp_path: Path) -> None:
    """Test log format is case insensitive."""
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"log_format": "json"}, f)

    config = Config.from_file(config_file)
    assert config.log_format == LogFormat.JSON

    with open(config_file, "w") as f:
        yaml.dump({"log_format": "TEXT"}, f)

    config = Config.from_file(config_file)
    assert config.log_format == LogFormat.TEXT


@pytest.fixture
def config_file_with_format(tmp_path: Path) -> Path:
    """Create a config file with log format."""
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"log_format": "TEXT", "log_level": "DEBUG"}, f)
    return config_file


def test_env_var_priority(config_file_with_format: Path) -> None:
    """Test environment variable priority for log format."""
    os.environ["CODEGATE_LOG_FORMAT"] = "JSON"
    try:
        config = Config.load(config_path=config_file_with_format)
        assert config.log_format == LogFormat.JSON  # env var overrides file
    finally:
        del os.environ["CODEGATE_LOG_FORMAT"]
