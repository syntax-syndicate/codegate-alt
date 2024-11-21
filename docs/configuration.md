# Configuration System

The configuration system in Codegate is managed through the `Config` class in `config.py`. It supports multiple configuration sources with a clear priority order.

## Configuration Priority (highest to lowest)

1. CLI arguments
2. Environment variables
3. Config file (YAML)
4. Default values

## Default Configuration Values

- Port: 8989
- Host: "localhost"
- Log Level: "INFO"
- Log Format: "JSON"

## Configuration Methods

### From File

Load configuration from a YAML file:

```python
config = Config.from_file("config.yaml")
```

### From Environment Variables

Environment variables are automatically loaded with these mappings:

- `CODEGATE_APP_PORT`: Server port
- `CODEGATE_APP_HOST`: Server host
- `CODEGATE_APP_LOG_LEVEL`: Logging level
- `CODEGATE_LOG_FORMAT`: Log format

```python
config = Config.from_env()
```

## Configuration Options

### Log Levels

Available log levels (case-insensitive):

- `ERROR`
- `WARNING`
- `INFO`
- `DEBUG`

### Log Formats

Available log formats (case-insensitive):

- `JSON`
- `TEXT`

## Error Handling

The configuration system uses a custom `ConfigurationError` exception for handling configuration-related errors, such as:

- Invalid port numbers (must be between 1 and 65535)
- Invalid log levels
- Invalid log formats
- YAML parsing errors
- File reading errors
