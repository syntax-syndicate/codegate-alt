"""Command-line interface for codegate."""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Dict, Optional, Set

import click
import structlog
from uvicorn.config import Config as UvicornConfig
from uvicorn.server import Server

from codegate.codegate_logging import LogFormat, LogLevel, setup_logging
from codegate.config import Config, ConfigurationError
from codegate.db.connection import init_db
from codegate.server import init_app
from codegate.providers.github.provider import run_proxy_server
from codegate.storage.utils import restore_storage_backup
from codegate.ca.codegate_ca import CertificateAuthority


class UvicornServer:
    """Wrapper for running uvicorn with asyncio."""

    def __init__(self, app, host: str, port: int, log_level: str):
        self.config = UvicornConfig(
            app=app,
            host=host,
            port=port,
            log_level=log_level,
            log_config=None
        )
        self.server = None
        self._startup_complete = asyncio.Event()
        self._shutdown_event = asyncio.Event()

    async def serve(self):
        """Start uvicorn server."""
        self.server = Server(config=self.config)
        self.server.force_exit = True
        try:
            self._startup_complete.set()
            await self.server.serve()
        except Exception as e:
            logger = structlog.get_logger("codegate")
            logger.error(f"Server error: {str(e)}")
            raise
        finally:
            await self.cleanup()

    async def wait_for_startup(self):
        """Wait for server to start up."""
        await self._startup_complete.wait()

    async def cleanup(self):
        """Cleanup server resources."""
        if self.server:
            self.server.should_exit = True
            # Signal the server to exit
            if hasattr(self.server, 'force_exit'):
                self.server.force_exit = True
            # Cancel any pending tasks
            for task in asyncio.all_tasks():
                if task is not asyncio.current_task():
                    task.cancel()


async def setup_and_run_servers(
    port: Optional[int],
    host: Optional[str],
    log_level: Optional[str],
    log_format: Optional[str],
    config: Optional[Path],
    prompts: Optional[Path],
    vllm_url: Optional[str],
    openai_url: Optional[str],
    anthropic_url: Optional[str],
    ollama_url: Optional[str],
    model_base_path: Optional[str],
    embedding_model: Optional[str],
):
    """Set up and run both FastAPI and proxy server with proper async handling."""
    logger = structlog.get_logger("codegate")

    try:
        # Create provider URLs dict from CLI options
        cli_provider_urls: Dict[str, str] = {}
        if vllm_url:
            cli_provider_urls["vllm"] = vllm_url
        if openai_url:
            cli_provider_urls["openai"] = openai_url
        if anthropic_url:
            cli_provider_urls["anthropic"] = anthropic_url
        if ollama_url:
            cli_provider_urls["ollama"] = ollama_url

        # Load configuration with priority resolution
        cfg = Config.load(
            config_path=config,
            prompts_path=prompts,
            cli_port=port,
            cli_host=host,
            cli_log_level=log_level,
            cli_log_format=log_format,
            cli_provider_urls=cli_provider_urls,
            model_base_path=model_base_path,
            embedding_model=embedding_model,
        )

        CertificateAuthority()

        setup_logging(cfg.log_level, cfg.log_format)

        # Initialize database
        await init_db()

        # Initialize FastAPI app
        app = init_app()

        # Create uvicorn server instance
        uvicorn_server = UvicornServer(
            app=app,
            host=cfg.host,
            port=cfg.port,
            log_level=cfg.log_level.value.lower()
        )

        # Set up signal handlers
        def signal_handler():
            logger.info("Received shutdown signal")
            asyncio.create_task(shutdown())

        async def shutdown():
            await uvicorn_server.cleanup()
            # Cancel all tasks except the current one
            for task in asyncio.all_tasks():
                if task is not asyncio.current_task():
                    task.cancel()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        # Create tasks for both servers
        tasks = [
            # asyncio.create_task(uvicorn_server.serve()),
            asyncio.create_task(run_proxy_server())
        ]

        # Wait for both servers to complete or for interruption
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled")
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            raise
        finally:
            # Ensure cleanup is called
            await uvicorn_server.cleanup()
            # Cancel any remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Server startup failed: {str(e)}")
        raise


def validate_port(ctx: click.Context, param: click.Parameter, value: int) -> int:
    """Validate the port number is in valid range."""
    if value is not None and not (1 <= value <= 65535):
        raise click.BadParameter("Port must be between 1 and 65535")
    return value


@click.group()
@click.version_option()
def cli() -> None:
    """Codegate - A configurable service gateway."""
    pass


@cli.command()
@click.option(
    "--prompts",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=False,
    help="Path to YAML prompts file (optional, shows default prompts if not provided)",
)
def show_prompts(prompts: Optional[Path]) -> None:
    """Display prompts from the specified file or default if no file specified."""
    try:
        cfg = Config.load(prompts_path=prompts)
        click.echo("Loaded prompts:")
        click.echo("-" * 40)
        for name, content in cfg.prompts.prompts.items():
            click.echo(f"\n{name}:")
            click.echo(f"{content}")
            click.echo("-" * 40)
    except ConfigurationError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--port",
    type=int,
    default=None,
    callback=validate_port,
    help="Port to listen on (default: 8989)",
)
@click.option(
    "--host",
    type=str,
    default=None,
    help="Host to bind to (default: localhost)",
)
@click.option(
    "--log-level",
    type=click.Choice([level.value for level in LogLevel]),
    default=None,
    help="Set the log level (default: INFO)",
)
@click.option(
    "--log-format",
    type=click.Choice([fmt.value for fmt in LogFormat], case_sensitive=False),
    default=None,
    help="Set the log format (default: JSON)",
)
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to YAML config file",
)
@click.option(
    "--prompts",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to YAML prompts file",
)
@click.option(
    "--vllm-url",
    type=str,
    default=None,
    help="vLLM provider URL (default: http://localhost:8000/v1)",
)
@click.option(
    "--openai-url",
    type=str,
    default=None,
    help="OpenAI provider URL (default: https://api.openai.com/v1)",
)
@click.option(
    "--anthropic-url",
    type=str,
    default=None,
    help="Anthropic provider URL (default: https://api.anthropic.com/v1)",
)
@click.option(
    "--ollama-url",
    type=str,
    default=None,
    help="Ollama provider URL (default: http://localhost:11434/api)",
)
@click.option(
    "--model-base-path",
    type=str,
    default="./models",
    help="Path to the model base directory",
)
@click.option(
    "--embedding-model",
    type=str,
    default="all-minilm-L6-v2-q5_k_m.gguf",
    help="Name of the model to use for embeddings",
)
def serve(
    port: Optional[int],
    host: Optional[str],
    log_level: Optional[str],
    log_format: Optional[str],
    config: Optional[Path],
    prompts: Optional[Path],
    vllm_url: Optional[str],
    openai_url: Optional[str],
    anthropic_url: Optional[str],
    ollama_url: Optional[str],
    model_base_path: Optional[str],
    embedding_model: Optional[str],
) -> None:
    """Start the codegate server."""
    try:
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the async setup and server
        try:
            loop.run_until_complete(
                setup_and_run_servers(
                    port,
                    host,
                    log_level,
                    log_format,
                    config,
                    prompts,
                    vllm_url,
                    openai_url,
                    anthropic_url,
                    ollama_url,
                    model_base_path,
                    embedding_model,
                )
            )
        except KeyboardInterrupt:
            logger = structlog.get_logger("codegate")
            logger.info("Shutting down server")
        finally:
            # Clean up pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            # Wait for tasks to complete with a timeout
            if pending:
                loop.run_until_complete(asyncio.wait(pending, timeout=5))
            loop.close()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--backup-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory path where the backup file is located.",
)
@click.option(
    "--backup-name",
    type=str,
    required=True,
    help="Name of the backup file to restore.",
)
def restore_backup(backup_path: Path, backup_name: str) -> None:
    """Restore the database from the specified backup."""
    try:
        restore_storage_backup(backup_path, backup_name)
        click.echo(f"Successfully restored the backup '{backup_name}' from {backup_path}.")
    except Exception as e:
        click.echo(f"Error restoring backup: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
