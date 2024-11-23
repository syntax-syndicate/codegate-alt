# Development Guide

This guide provides comprehensive information for developers working on the Codegate project.

## Project Overview

Codegate is a configurable Generative AI gateway designed to protect developers from potential AI-related security risks. Key features include:
- Secrets exfiltration prevention
- Secure coding recommendations
- Prevention of AI recommending deprecated/malicious libraries

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management
- [Docker](https://docs.docker.com/get-docker/) (for containerized deployment)
- or
- [PodMan](https://podman.io/getting-started/installation) (for containerized deployment)
- [VSCode](https://code.visualstudio.com/download) (recommended IDE)

### Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/stacklok/codegate.git
   cd codegate
   ```

2. Install Poetry following the [official installation guide](https://python-poetry.org/docs/#installation)

3. Install project dependencies:
   ```bash
   poetry install --with dev
   ```

## Project Structure

```
codegate/
├── pyproject.toml    # Project configuration and dependencies
├── poetry.lock      # Lock file (committed to version control)
├── src/
│   └── codegate/    # Source code
│       ├── __init__.py
│       ├── cli.py           # Command-line interface
│       ├── config.py        # Configuration management
│       ├── logging.py       # Logging setup
│       ├── server.py        # Main server implementation
│       └── providers/*      # External service providers (anthropic, openai, etc.)
├── tests/           # Test files
└── docs/            # Documentation
```

## Development Workflow

### 1. Environment Management

Poetry commands for managing your development environment:

- `poetry install`: Install project dependencies
- `poetry add package-name`: Add a new package dependency
- `poetry add --group dev package-name`: Add a development dependency
- `poetry remove package-name`: Remove a package
- `poetry update`: Update dependencies to their latest versions
- `poetry show`: List all installed packages
- `poetry env info`: Show information about the virtual environment

### 2. Code Style and Quality

The project uses several tools to maintain code quality:

- **Black** for code formatting:
  ```bash
  poetry run black .
  ```

- **Ruff** for linting:
  ```bash
  poetry run ruff check .
  ```

- **Bandit** for security checks:
  ```bash
  poetry run bandit -r src/
  ```

### 3. Testing

Run the test suite with coverage:
```bash
poetry run pytest
```

Tests are located in the `tests/` directory and follow the same structure as the source code.

### 4. Make Commands

The project includes a Makefile for common development tasks:

- `make install`: Install all dependencies
- `make format`: Format code using black and ruff
- `make lint`: Run linting checks
- `make test`: Run tests with coverage
- `make security`: Run security checks
- `make build`: Build distribution packages
- `make all`: Run all checks and build (recommended before committing)

## Configuration System

Codegate uses a hierarchical configuration system with the following priority (highest to lowest):

1. CLI arguments
2. Environment variables
3. Config file (YAML)
4. Default values

### Configuration Options

- Port: Server port (default: 8989)
- Host: Server host (default: "localhost")
- Log Level: Logging level (ERROR|WARNING|INFO|DEBUG)
- Log Format: Log format (JSON|TEXT)

See [Configuration Documentation](configuration.md) for detailed information.

## CLI Interface

The main command-line interface is implemented in `cli.py`. Basic usage:

```bash
# Start server with default settings
codegate serve

# Start with custom configuration
codegate serve --port 8989 --host localhost --log-level DEBUG
```

See [CLI Documentation](cli.md) for detailed command information.

## Dependencies Management

### Adding Dependencies

For runtime dependencies:
```bash
poetry add package-name
```

For development dependencies:
```bash
poetry add --group dev package-name
```

### Updating Dependencies

To update all dependencies:
```bash
poetry update
```

To update a specific package:
```bash
poetry update package-name
```

## Virtual Environment

Poetry automatically manages virtual environments. To activate:

```bash
poetry shell
```

To run a single command:

```bash
poetry run command
```

## Building and Publishing

To build distribution packages:
```bash
poetry build
```

To publish to PyPI:
```bash
poetry publish
```

## Debugging Tips

1. Use DEBUG log level for detailed logging:
   ```bash
   codegate serve --log-level DEBUG
   ```

2. Use TEXT log format for human-readable logs during development:
   ```bash
   codegate serve --log-format TEXT
   ```

3. Check the configuration resolution by examining logs at startup

## Contributing Guidelines

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass with `make test`
4. Run `make all` before committing to ensure:
   - Code is properly formatted
   - All linting checks pass
   - Tests pass with good coverage
   - Security checks pass
5. Update documentation as needed
6. Submit a pull request

## Best Practices

1. Always commit both `pyproject.toml` and `poetry.lock` files
2. Use `poetry add` instead of manually editing `pyproject.toml`
3. Run `make all` before committing changes
4. Use `poetry run` prefix for Python commands
5. Keep dependencies minimal and well-organized
6. Write descriptive commit messages
7. Add tests for new functionality
8. Update documentation when making significant changes
9. Follow the existing code style and patterns
10. Use type hints and docstrings for better code documentation

## Common Issues and Solutions

1. **Virtual Environment Issues**
   - Reset Poetry's virtual environment:
     ```bash
     poetry env remove python
     poetry install
     ```

2. **Dependency Conflicts**
   - Update poetry.lock:
     ```bash
     poetry update
     ```
   - Check dependency tree:
     ```bash
     poetry show --tree
     ```

3. **Test Failures**
   - Run specific test:
     ```bash
     poetry run pytest tests/test_specific.py -v
     ```
   - Debug with more output:
     ```bash
     poetry run pytest -vv --pdb
