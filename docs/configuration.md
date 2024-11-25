# Configuration System

The configuration system in Codegate is managed through the `Config` class in `config.py`. It supports multiple configuration sources with a clear priority order.

## Configuration Priority (highest to lowest)

1. CLI arguments
2. Environment variables
3. Config file (YAML)
4. Default values (including default prompts from prompts/default.yaml)

## Default Configuration Values

- Port: 8989
- Host: "localhost"
- Log Level: "INFO"
- Log Format: "JSON"
- Prompts: Default prompts from prompts/default.yaml

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
- `CODEGATE_PROMPTS_FILE`: Path to prompts YAML file

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

### Prompts Configuration

Prompts can be configured in several ways:

1. Default Prompts:
   - Located in prompts/default.yaml
   - Loaded automatically if no other prompts are specified

2. In Configuration File:
   ```yaml
   # Option 1: Direct prompts definition
   prompts:
     my_prompt: "Custom prompt text"
     another_prompt: "Another prompt text"

   # Option 2: Reference to prompts file
   prompts: "path/to/prompts.yaml"
   ```

3. Via Environment Variable:
   ```bash
   export CODEGATE_PROMPTS_FILE=path/to/prompts.yaml
   ```

4. Via CLI Flag:
   ```bash
   codegate serve --prompts path/to/prompts.yaml
   ```

### Prompts File Format

Prompts files should be in YAML format with string values:

```yaml
prompt_name: "Prompt text content"
another_prompt: "More prompt text"
```

Access prompts in code:
```python
config = Config.load()
prompt = config.prompts.prompt_name
```

## Error Handling

The configuration system uses a custom `ConfigurationError` exception for handling configuration-related errors, such as:

- Invalid port numbers (must be between 1 and 65535)
- Invalid log levels
- Invalid log formats
- YAML parsing errors
- File reading errors
- Invalid prompt values (must be strings)
- Missing or invalid prompts files
