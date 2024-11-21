"""Tests for command-line interface."""

from pathlib import Path
from typing import Any, Generator
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from codegate.cli import cli
from codegate.config import LogFormat, LogLevel


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_logging() -> Generator[Any, None, None]:
    """Mock the logging setup."""
    with patch("codegate.cli.setup_logging") as mock:
        yield mock


def test_cli_version(cli_runner: CliRunner) -> None:
    """Test CLI version command."""
    result = cli_runner.invoke(cli, ["--version"])
    assert "version" in result.output.lower()


def test_serve_default_options(cli_runner: CliRunner, mock_logging: Any) -> None:
    """Test serve command with default options."""
    with patch("logging.getLogger") as mock_logger:
        logger_instance = mock_logger.return_value
        result = cli_runner.invoke(cli, ["serve"])

        assert result.exit_code == 0
        mock_logging.assert_called_once_with(LogLevel.INFO, LogFormat.JSON)
        logger_instance.info.assert_any_call(
            "Starting server",
            extra={
                "host": "localhost",
                "port": 8989,
                "log_level": "INFO",
                "log_format": "JSON",
            }
        )


def test_serve_custom_options(cli_runner: CliRunner, mock_logging: Any) -> None:
    """Test serve command with custom options."""
    with patch("logging.getLogger") as mock_logger:
        logger_instance = mock_logger.return_value
        result = cli_runner.invoke(
            cli,
            [
                "serve",
                "--port", "8989",
                "--host", "localhost",
                "--log-level", "DEBUG",
                "--log-format", "TEXT"
            ]
        )

        assert result.exit_code == 0
        mock_logging.assert_called_once_with(LogLevel.DEBUG, LogFormat.TEXT)
        logger_instance.info.assert_any_call(
            "Starting server",
            extra={
                "host": "localhost",
                "port": 8989,
                "log_level": "DEBUG",
                "log_format": "TEXT",
            }
        )


def test_serve_invalid_port(cli_runner: CliRunner) -> None:
    """Test serve command with invalid port."""
    result = cli_runner.invoke(cli, ["serve", "--port", "0"])
    assert result.exit_code != 0
    assert "Port must be between 1 and 65535" in result.output

    result = cli_runner.invoke(cli, ["serve", "--port", "65536"])
    assert result.exit_code != 0
    assert "Port must be between 1 and 65535" in result.output


def test_serve_invalid_log_level(cli_runner: CliRunner) -> None:
    """Test serve command with invalid log level."""
    result = cli_runner.invoke(cli, ["serve", "--log-level", "INVALID"])
    assert result.exit_code != 0
    assert "Invalid value for '--log-level'" in result.output


def test_serve_with_config_file(
    cli_runner: CliRunner,
    mock_logging: Any,
    temp_config_file: Path
) -> None:
    """Test serve command with config file."""
    with patch("logging.getLogger") as mock_logger:
        logger_instance = mock_logger.return_value
        result = cli_runner.invoke(cli, ["serve", "--config", str(temp_config_file)])

        assert result.exit_code == 0
        mock_logging.assert_called_once_with(LogLevel.DEBUG, LogFormat.JSON)
        logger_instance.info.assert_any_call(
            "Starting server",
            extra={
                "host": "localhost",
                "port": 8989,
                "log_level": "DEBUG",
                "log_format": "JSON",
            }
        )

def test_serve_with_nonexistent_config_file(cli_runner: CliRunner) -> None:
    """Test serve command with nonexistent config file."""
    result = cli_runner.invoke(cli, ["serve", "--config", "nonexistent.yaml"])
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_serve_priority_resolution(
    cli_runner: CliRunner,
    mock_logging: Any,
    temp_config_file: Path,
    env_vars: Any
) -> None:
    """Test serve command respects configuration priority."""
    with patch("logging.getLogger") as mock_logger:
        logger_instance = mock_logger.return_value
        result = cli_runner.invoke(
            cli,
            [
                "serve",
                "--config", str(temp_config_file),
                "--port", "8080",
                "--host", "example.com",
                "--log-level", "ERROR",
                "--log-format", "TEXT"
            ]
        )

        assert result.exit_code == 0
        mock_logging.assert_called_once_with(LogLevel.ERROR, LogFormat.TEXT)
        logger_instance.info.assert_any_call(
            "Starting server",
            extra={
                "host": "example.com",
                "port": 8080,
                "log_level": "ERROR",
                "log_format": "TEXT",
            }
        )


def test_main_function() -> None:
    """Test main entry point function."""
    with patch("codegate.cli.cli") as mock_cli:
        from codegate.cli import main
        main()
        mock_cli.assert_called_once()
