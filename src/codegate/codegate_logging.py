import logging
import sys
from enum import Enum
from typing import Optional

import structlog


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


def setup_logging(
    log_level: Optional[LogLevel] = None, log_format: Optional[LogFormat] = None
) -> logging.Logger:
    """Configure the logging system.

    Args:
        log_level: The logging level to use. Defaults to INFO if not specified.
        log_format: The log format to use. Defaults to JSON if not specified.

    This configures two handlers:
    - stderr_handler: For ERROR, CRITICAL, and WARNING messages
    - stdout_handler: For INFO and DEBUG messages
    """
    if log_level is None:
        log_level = LogLevel.INFO
    if log_format is None:
        log_format = LogFormat.JSON

    # The configuration was taken from structlog documentation
    # https://www.structlog.org/en/stable/standard-library.html
    # Specifically the section "Rendering Using structlog-based Formatters Within logging"

    # Adds log level and timestamp to log entries
    shared_processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%dT%H:%M:%S.%03dZ", utc=True),
    ]
    # Not sure why this is needed. I think it is a wrapper for the standard logging module.
    # Should allow to log both with structlog and the standard logging module:
    # import logging
    # import structlog
    # logging.getLogger("stdlog").info("woo")
    # structlog.get_logger("structlog").info("amazing", events="oh yes")
    structlog.configure(
        processors=shared_processors
        + [
            # Prepare event dict for `ProcessorFormatter`.
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # The config aboves adds the following keys to all log entries: _record & _from_structlog.
    # remove_processors_meta removes them.
    processors = shared_processors + [structlog.stdlib.ProcessorFormatter.remove_processors_meta]
    # Choose the processors based on the log format
    if log_format == LogFormat.JSON:
        processors = processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = processors + [structlog.dev.ConsoleRenderer()]
    formatter = structlog.stdlib.ProcessorFormatter(
        # foreign_pre_chain run ONLY on `logging` entries that do NOT originate within structlog.
        foreign_pre_chain=shared_processors,
        processors=processors,
    )

    # Create handlers for stdout and stderr
    stdout_handler = logging.StreamHandler(sys.stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)

    # Set formatters
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)

    # Configure log routing
    stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    stderr_handler.addFilter(lambda record: record.levelno > logging.INFO)

    # Get root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.value)

    # Remove any existing handlers and add our new ones
    root_logger.handlers.clear()
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(stderr_handler)

    # Create a logger for our package
    logger = structlog.get_logger("codegate")
    logger.debug(
        "Logging initialized",
        extra={
            "log_level": log_level.value,
            "log_format": log_format.value,
            "handlers": ["stdout", "stderr"],
        },
    )
