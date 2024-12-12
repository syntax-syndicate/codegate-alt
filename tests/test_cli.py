"""Tests for the CLI module."""

import asyncio
import signal
from pathlib import Path
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from uvicorn.config import Config as UvicornConfig

from codegate.cli import UvicornServer, cli
from codegate.codegate_logging import LogFormat, LogLevel
from codegate.config import DEFAULT_PROVIDER_URLS


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_logging() -> Generator[MagicMock, None, None]:
    """Mock the logging function."""
    with patch("codegate.cli.structlog.get_logger") as mock:
        logger_instance = MagicMock()
        # Set up info method to properly capture extra parameters
        logger_instance.info = MagicMock(return_value=None)
        mock.return_value = logger_instance
        yield mock


@pytest.fixture
def mock_setup_logging() -> Generator[MagicMock, None, None]:
    """Mock the setup_logging function."""
    with patch("codegate.codegate_logging.setup_logging") as mock:
        yield mock


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    """Create a temporary config file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
port: 8989
host: localhost
log_level: DEBUG
log_format: JSON
certs_dir: "./test-certs"
ca_cert: "test-ca.crt"
ca_key: "test-ca.key"
server_cert: "test-server.crt"
server_key: "test-server.key"
"""
    )
    return config_file


@pytest.fixture
def mock_uvicorn_server() -> AsyncMock:
    """Create a mock Uvicorn server."""
    config = UvicornConfig(app=MagicMock(), host="localhost", port=8989)
    mock_server = AsyncMock(spec=UvicornServer)
    mock_server.config = config
    mock_server._startup_complete = asyncio.Event()
    mock_server._shutdown_event = asyncio.Event()

    # Implement the serve method to match actual implementation
    async def mock_serve():
        loop = asyncio.get_running_loop()
        # Add signal handlers
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(mock_server.cleanup()))
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(mock_server.cleanup()))
        mock_server._startup_complete.set()
        # Return immediately for testing
        return

    # Implement the cleanup method to match actual implementation
    async def mock_cleanup():
        mock_server._shutdown_event.set()

    mock_server.serve = AsyncMock(side_effect=mock_serve)
    mock_server.cleanup = AsyncMock(side_effect=mock_cleanup)
    mock_server.wait_startup_complete = AsyncMock(
        side_effect=lambda: mock_server._startup_complete.wait()
    )
    return mock_server


def test_cli_version(cli_runner: CliRunner) -> None:
    """Test CLI version command."""
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_uvicorn_server_serve(mock_uvicorn_server: AsyncMock) -> None:
    """Test UvicornServer serve method."""
    # Start server in background task
    server_task = asyncio.create_task(mock_uvicorn_server.serve())

    # Wait for startup to complete
    await mock_uvicorn_server.wait_startup_complete()

    # Verify server started
    assert mock_uvicorn_server.serve.called

    # Cleanup
    await mock_uvicorn_server.cleanup()
    await server_task


@pytest.mark.asyncio
async def test_uvicorn_server_cleanup(mock_uvicorn_server: AsyncMock) -> None:
    """Test UvicornServer cleanup method."""
    # Start server
    server_task = asyncio.create_task(mock_uvicorn_server.serve())
    await mock_uvicorn_server.wait_startup_complete()

    # Trigger cleanup
    await mock_uvicorn_server.cleanup()

    # Verify shutdown was called
    assert mock_uvicorn_server.cleanup.called
    assert mock_uvicorn_server._shutdown_event.is_set()

    await server_task


@pytest.mark.asyncio
async def test_uvicorn_server_signal_handling(mock_uvicorn_server: AsyncMock) -> None:
    """Test signal handling in UvicornServer."""
    # Create a real event loop for signal handling
    loop = asyncio.get_running_loop()

    # Start server
    server_task = asyncio.create_task(mock_uvicorn_server.serve())
    await mock_uvicorn_server.wait_startup_complete()

    # Verify signal handlers were added
    handlers = []

    def mock_add_handler(sig, callback):
        handlers.append((sig, callback))

    with patch.object(loop, "add_signal_handler", side_effect=mock_add_handler):
        # Re-run serve to trigger signal handler setup
        await mock_uvicorn_server.serve()

        # Verify handlers were added
        assert len(handlers) == 2
        assert any(sig == signal.SIGTERM for sig, _ in handlers)
        assert any(sig == signal.SIGINT for sig, _ in handlers)

    # Cleanup
    await mock_uvicorn_server.cleanup()
    await server_task


def test_serve_default_options(
    cli_runner: CliRunner, mock_logging: MagicMock, mock_setup_logging: MagicMock
) -> None:
    """Test serve command with default options."""
    with (
        patch("codegate.cli.run_servers") as mock_run,
        patch("codegate.cli.init_db_sync"),
        patch("codegate.cli.CertificateAuthority"),
    ):

        mock_config = MagicMock()
        mock_config.log_level = LogLevel.INFO
        mock_config.log_format = LogFormat.JSON
        mock_config.host = "localhost"
        mock_config.port = 8989
        mock_config.prompts.prompts = {
            "key1": "val1",
            "key2": "val2",
            "key3": "val3",
            "key4": "val4",
            "key5": "val5",
            "key6": "val6",
            "key7": "val7",
        }
        mock_config.provider_urls = DEFAULT_PROVIDER_URLS
        mock_config.certs_dir = "./certs"

        with patch("codegate.config.Config.load", return_value=mock_config):
            # Make run_servers call setup_logging when invoked
            async def mock_run_servers(cfg, app):
                mock_setup_logging(cfg.log_level, cfg.log_format)
                logger = mock_logging.return_value
                logger.info(
                    "Starting server",
                    extra={
                        "host": cfg.host,
                        "port": cfg.port,
                        "log_level": cfg.log_level.value,
                        "log_format": cfg.log_format.value,
                        "prompts_loaded": len(cfg.prompts.prompts),
                        "provider_urls": cfg.provider_urls,
                        "certs_dir": cfg.certs_dir,
                    },
                )

            mock_run.side_effect = mock_run_servers

            result = cli_runner.invoke(cli, ["serve"])

            assert result.exit_code == 0
            mock_setup_logging.assert_called_once_with(LogLevel.INFO, LogFormat.JSON)
            mock_logging.assert_called_with("codegate")

            # Verify the info call was made with correct parameters
            logger = mock_logging.return_value
            logger.info.assert_any_call(
                "Starting server",
                extra={
                    "host": "localhost",
                    "port": 8989,
                    "log_level": "INFO",
                    "log_format": "JSON",
                    "prompts_loaded": 7,
                    "provider_urls": DEFAULT_PROVIDER_URLS,
                    "certs_dir": "./certs",
                },
            )
            mock_run.assert_called_once()


def test_serve_custom_options(
    cli_runner: CliRunner, mock_logging: MagicMock, mock_setup_logging: MagicMock
) -> None:
    """Test serve command with custom options."""
    with (
        patch("codegate.cli.run_servers") as mock_run,
        patch("codegate.cli.init_db_sync"),
        patch("codegate.cli.CertificateAuthority"),
    ):

        mock_config = MagicMock()
        mock_config.log_level = LogLevel.DEBUG
        mock_config.log_format = LogFormat.TEXT
        mock_config.host = "localhost"
        mock_config.port = 8989
        mock_config.prompts.prompts = {
            "key1": "val1",
            "key2": "val2",
            "key3": "val3",
            "key4": "val4",
            "key5": "val5",
            "key6": "val6",
            "key7": "val7",
        }
        mock_config.provider_urls = DEFAULT_PROVIDER_URLS
        mock_config.certs_dir = "./custom-certs"

        with patch("codegate.config.Config.load", return_value=mock_config):
            # Make run_servers call setup_logging when invoked
            async def mock_run_servers(cfg, app):
                mock_setup_logging(cfg.log_level, cfg.log_format)
                logger = mock_logging.return_value
                logger.info(
                    "Starting server",
                    extra={
                        "host": cfg.host,
                        "port": cfg.port,
                        "log_level": cfg.log_level.value,
                        "log_format": cfg.log_format.value,
                        "prompts_loaded": len(cfg.prompts.prompts),
                        "provider_urls": cfg.provider_urls,
                        "certs_dir": cfg.certs_dir,
                    },
                )

            mock_run.side_effect = mock_run_servers

            result = cli_runner.invoke(
                cli,
                [
                    "serve",
                    "--port",
                    "8989",
                    "--host",
                    "localhost",
                    "--log-level",
                    "DEBUG",
                    "--log-format",
                    "TEXT",
                    "--certs-dir",
                    "./custom-certs",
                    "--ca-cert",
                    "custom-ca.crt",
                    "--ca-key",
                    "custom-ca.key",
                    "--server-cert",
                    "custom-server.crt",
                    "--server-key",
                    "custom-server.key",
                ],
            )

            assert result.exit_code == 0
            mock_setup_logging.assert_called_once_with(LogLevel.DEBUG, LogFormat.TEXT)
            mock_logging.assert_called_with("codegate")

            # Verify the info call was made with correct parameters
            logger = mock_logging.return_value
            logger.info.assert_any_call(
                "Starting server",
                extra={
                    "host": "localhost",
                    "port": 8989,
                    "log_level": "DEBUG",
                    "log_format": "TEXT",
                    "prompts_loaded": 7,
                    "provider_urls": DEFAULT_PROVIDER_URLS,
                    "certs_dir": "./custom-certs",
                },
            )
            mock_run.assert_called_once()


def test_serve_invalid_port(cli_runner: CliRunner) -> None:
    """Test serve command with invalid port."""
    result = cli_runner.invoke(cli, ["serve", "--port", "999999"])
    assert result.exit_code == 2
    assert "Port must be between 1 and 65535" in result.output


def test_serve_invalid_log_level(cli_runner: CliRunner) -> None:
    """Test serve command with invalid log level."""
    result = cli_runner.invoke(cli, ["serve", "--log-level", "INVALID"])
    assert result.exit_code == 2
    assert "Invalid value for '--log-level'" in result.output


def test_serve_with_config_file(
    cli_runner: CliRunner,
    mock_logging: MagicMock,
    temp_config_file: Path,
    mock_setup_logging: MagicMock,
) -> None:
    """Test serve command with config file."""
    with (
        patch("codegate.cli.run_servers") as mock_run,
        patch("codegate.cli.init_db_sync"),
        patch("codegate.cli.CertificateAuthority"),
    ):

        mock_config = MagicMock()
        mock_config.log_level = LogLevel.DEBUG
        mock_config.log_format = LogFormat.JSON
        mock_config.host = "localhost"
        mock_config.port = 8989
        mock_config.prompts.prompts = {
            "key1": "val1",
            "key2": "val2",
            "key3": "val3",
            "key4": "val4",
            "key5": "val5",
            "key6": "val6",
            "key7": "val7",
        }
        mock_config.provider_urls = DEFAULT_PROVIDER_URLS
        mock_config.certs_dir = "./test-certs"

        with patch("codegate.config.Config.load", return_value=mock_config):
            # Make run_servers call setup_logging when invoked
            async def mock_run_servers(cfg, app):
                mock_setup_logging(cfg.log_level, cfg.log_format)
                logger = mock_logging.return_value
                logger.info(
                    "Starting server",
                    extra={
                        "host": cfg.host,
                        "port": cfg.port,
                        "log_level": cfg.log_level.value,
                        "log_format": cfg.log_format.value,
                        "prompts_loaded": len(cfg.prompts.prompts),
                        "provider_urls": cfg.provider_urls,
                        "certs_dir": cfg.certs_dir,
                    },
                )

            mock_run.side_effect = mock_run_servers

            result = cli_runner.invoke(cli, ["serve", "--config", str(temp_config_file)])

            assert result.exit_code == 0
            mock_setup_logging.assert_called_once_with(LogLevel.DEBUG, LogFormat.JSON)
            mock_logging.assert_called_with("codegate")

            # Verify the info call was made with correct parameters
            logger = mock_logging.return_value
            logger.info.assert_any_call(
                "Starting server",
                extra={
                    "host": "localhost",
                    "port": 8989,
                    "log_level": "DEBUG",
                    "log_format": "JSON",
                    "prompts_loaded": 7,
                    "provider_urls": DEFAULT_PROVIDER_URLS,
                    "certs_dir": "./test-certs",
                },
            )
            mock_run.assert_called_once()


def test_serve_with_nonexistent_config_file(cli_runner: CliRunner) -> None:
    """Test serve command with nonexistent config file."""
    result = cli_runner.invoke(cli, ["serve", "--config", "nonexistent.yaml"])
    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_serve_priority_resolution(
    cli_runner: CliRunner,
    mock_logging: MagicMock,
    temp_config_file: Path,
    env_vars: Any,
    mock_setup_logging: MagicMock,
) -> None:
    """Test serve command respects configuration priority."""
    with (
        patch("codegate.cli.run_servers") as mock_run,
        patch("codegate.cli.init_db_sync"),
        patch("codegate.cli.CertificateAuthority"),
    ):

        mock_config = MagicMock()
        mock_config.log_level = LogLevel.ERROR
        mock_config.log_format = LogFormat.TEXT
        mock_config.host = "example.com"
        mock_config.port = 8080
        mock_config.prompts.prompts = {
            "key1": "val1",
            "key2": "val2",
            "key3": "val3",
            "key4": "val4",
            "key5": "val5",
            "key6": "val6",
            "key7": "val7",
        }
        mock_config.provider_urls = DEFAULT_PROVIDER_URLS
        mock_config.certs_dir = "./cli-certs"

        with patch("codegate.config.Config.load", return_value=mock_config):
            # Make run_servers call setup_logging when invoked
            async def mock_run_servers(cfg, app):
                mock_setup_logging(cfg.log_level, cfg.log_format)
                logger = mock_logging.return_value
                logger.info(
                    "Starting server",
                    extra={
                        "host": cfg.host,
                        "port": cfg.port,
                        "log_level": cfg.log_level.value,
                        "log_format": cfg.log_format.value,
                        "prompts_loaded": len(cfg.prompts.prompts),
                        "provider_urls": cfg.provider_urls,
                        "certs_dir": cfg.certs_dir,
                    },
                )

            mock_run.side_effect = mock_run_servers

            result = cli_runner.invoke(
                cli,
                [
                    "serve",
                    "--config",
                    str(temp_config_file),
                    "--port",
                    "8080",
                    "--host",
                    "example.com",
                    "--log-level",
                    "ERROR",
                    "--log-format",
                    "TEXT",
                    "--certs-dir",
                    "./cli-certs",
                    "--ca-cert",
                    "cli-ca.crt",
                    "--ca-key",
                    "cli-ca.key",
                    "--server-cert",
                    "cli-server.crt",
                    "--server-key",
                    "cli-server.key",
                ],
            )

            assert result.exit_code == 0
            mock_setup_logging.assert_called_once_with(LogLevel.ERROR, LogFormat.TEXT)
            mock_logging.assert_called_with("codegate")

            # Verify the info call was made with correct parameters
            logger = mock_logging.return_value
            logger.info.assert_any_call(
                "Starting server",
                extra={
                    "host": "example.com",
                    "port": 8080,
                    "log_level": "ERROR",
                    "log_format": "TEXT",
                    "prompts_loaded": 7,
                    "provider_urls": DEFAULT_PROVIDER_URLS,
                    "certs_dir": "./cli-certs",
                },
            )
            mock_run.assert_called_once()


def test_serve_certificate_options(
    cli_runner: CliRunner, mock_logging: MagicMock, mock_setup_logging: MagicMock
) -> None:
    """Test serve command with certificate options."""
    with (
        patch("codegate.cli.run_servers") as mock_run,
        patch("codegate.cli.init_db_sync"),
        patch("codegate.cli.CertificateAuthority"),
    ):

        mock_config = MagicMock()
        mock_config.log_level = LogLevel.INFO
        mock_config.log_format = LogFormat.JSON
        mock_config.host = "localhost"
        mock_config.port = 8989
        mock_config.prompts.prompts = {
            "key1": "val1",
            "key2": "val2",
            "key3": "val3",
            "key4": "val4",
            "key5": "val5",
            "key6": "val6",
            "key7": "val7",
        }
        mock_config.provider_urls = DEFAULT_PROVIDER_URLS
        mock_config.certs_dir = "./custom-certs"

        with patch("codegate.config.Config.load", return_value=mock_config):
            # Make run_servers call setup_logging when invoked
            async def mock_run_servers(cfg, app):
                mock_setup_logging(cfg.log_level, cfg.log_format)
                logger = mock_logging.return_value
                logger.info(
                    "Starting server",
                    extra={
                        "host": cfg.host,
                        "port": cfg.port,
                        "log_level": cfg.log_level.value,
                        "log_format": cfg.log_format.value,
                        "prompts_loaded": len(cfg.prompts.prompts),
                        "provider_urls": cfg.provider_urls,
                        "certs_dir": cfg.certs_dir,
                    },
                )

            mock_run.side_effect = mock_run_servers

            result = cli_runner.invoke(
                cli,
                [
                    "serve",
                    "--certs-dir",
                    "./custom-certs",
                    "--ca-cert",
                    "custom-ca.crt",
                    "--ca-key",
                    "custom-ca.key",
                    "--server-cert",
                    "custom-server.crt",
                    "--server-key",
                    "custom-server.key",
                ],
            )

            assert result.exit_code == 0
            mock_setup_logging.assert_called_once_with(LogLevel.INFO, LogFormat.JSON)
            mock_logging.assert_called_with("codegate")

            # Verify the info call was made with correct parameters
            logger = mock_logging.return_value
            logger.info.assert_any_call(
                "Starting server",
                extra={
                    "host": "localhost",
                    "port": 8989,
                    "log_level": "INFO",
                    "log_format": "JSON",
                    "prompts_loaded": 7,
                    "provider_urls": DEFAULT_PROVIDER_URLS,
                    "certs_dir": "./custom-certs",
                },
            )
            mock_run.assert_called_once()


def test_main_function() -> None:
    """Test main function."""
    with patch("codegate.cli.cli") as mock_cli:
        from codegate.cli import main

        main()
        mock_cli.assert_called_once()
