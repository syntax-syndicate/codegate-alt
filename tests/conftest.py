"""Test configuration and fixtures."""

import datetime
import json
import os
from pathlib import Path
from typing import Any, Generator, Iterator
from unittest.mock import patch

import pytest
import yaml

from codegate.config import Config


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Iterator[Path]:
    """Create a temporary config file."""
    config_data = {
        "port": 8989,
        "host": "localhost",
        "log_level": "DEBUG",
        "log_format": "JSON",
    }
    config_file = tmp_path / "config.yaml"

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    yield config_file


@pytest.fixture
def env_vars() -> Generator[None, None, None]:
    """Set up test environment variables."""
    original_env = dict(os.environ)

    os.environ.update(
        {
            "CODEGATE_APP_PORT": "8989",
            "CODEGATE_APP_HOST": "localhost",
            "CODEGATE_APP_LOG_LEVEL": "WARNING",
            "CODEGATE_LOG_FORMAT": "TEXT",
        }
    )

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def default_config() -> Config:
    """Create a default configuration instance."""
    return Config()


@pytest.fixture
def mock_datetime() -> Generator[None, None, None]:
    """Mock datetime to return a fixed time."""
    fixed_dt = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)

    with patch("datetime.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        mock_dt.fromtimestamp.return_value = fixed_dt
        mock_dt.UTC = datetime.UTC
        yield


@pytest.fixture
def capture_logs(tmp_path: Path) -> Iterator[Path]:
    """Capture logs to a file for testing."""
    log_file = tmp_path / "test.log"

    # Create a file handler
    import logging

    handler = logging.FileHandler(log_file)
    logger = logging.getLogger()
    logger.addHandler(handler)

    yield log_file

    # Clean up
    handler.close()
    logger.removeHandler(handler)


def parse_json_log(log_line: str) -> dict[str, Any]:
    """Parse a JSON log line into a dictionary."""
    try:
        return json.loads(log_line)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON log line: {e}")
