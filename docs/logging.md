# Logging System

The logging system in Codegate (`logging.py`) provides a flexible and structured logging solution with support for both JSON and text formats.

## Log Routing

Logs are automatically routed based on their level:

- **stdout**: INFO and DEBUG messages
- **stderr**: ERROR, CRITICAL, and WARNING messages

## Log Formats

### JSON Format

When using JSON format (default), log entries include:

```json
{
  "timestamp": "YYYY-MM-DDThh:mm:ss.mmmZ",
  "level": "LOG_LEVEL",
  "module": "MODULE_NAME",
  "message": "Log message",
  "extra": {
    // Additional fields as you desire
  }
}
```

### Text Format

When using text format, log entries follow this pattern:

```
YYYY-MM-DDThh:mm:ss.mmmZ - LEVEL - NAME - MESSAGE
```

## Features

- **Consistent Timestamps**: ISO-8601 format with millisecond precision in UTC
- **Automatic JSON Serialization**: Extra fields are automatically serialized to JSON
- **Non-serializable Handling**: Graceful handling of non-serializable values
- **Exception Support**: Full exception and stack trace integration
- **Dual Output**: Separate handlers for error and non-error logs
- **Configurable Levels**: Support for ERROR, WARNING, INFO, and DEBUG levels

## Usage Examples

### Basic Logging

```python
import logging

logger = logging.getLogger(__name__)

# Different log levels
logger.info("This is an info message")
logger.debug("This is a debug message")
logger.error("This is an error message")
logger.warning("This is a warning message")
```

### Logging with Extra Fields

```python
logger.info("Server starting", extra={
    "host": "localhost",
    "port": 8000,
    "environment": "production"
})
```

### Exception Logging

```python
try:
    # Some code that might raise an exception
    raise ValueError("Something went wrong")
except Exception as e:
    logger.error("Error occurred", exc_info=True)
```

## Configuration

The logging system can be configured through:

1. CLI arguments:
   ```bash
   codegate serve --log-level DEBUG --log-format TEXT
   ```

2. Environment variables:
   ```bash
   export APP_LOG_LEVEL=DEBUG
   export CODEGATE_LOG_FORMAT=TEXT
   ```

3. Configuration file:
   ```yaml
   log_level: DEBUG
   log_format: TEXT
   ```

## Best Practices

1. Always use the appropriate log level:
   - ERROR: For errors that need immediate attention
   - WARNING: For potentially harmful situations
   - INFO: For general operational information
   - DEBUG: For detailed information useful during development

2. Include relevant context in extra fields:
   ```python
   logger.info("User action", extra={
       "user_id": "123",
       "action": "login",
       "ip_address": "192.168.1.1"
   })
   ```

3. Use structured logging with JSON format in production for better log aggregation and analysis

4. Enable DEBUG level logging during development for maximum visibility
