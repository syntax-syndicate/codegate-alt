# Codegate

[![CI](https://github.com/stacklok/codegate/actions/workflows/ci.yml/badge.svg)](https://github.com/stacklok/codegate/actions/workflows/ci.yml)

A configurable Generative AI gateway, protecting developers from the dangers of AI.

## Features

- Secrets exflitration prevention
- Secure Coding recommendations
- Preventing AI from recommending deprecated and / or malicious libraries


### Installation

#### Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [jq](https://stedolan.github.io/jq/download/)
- [vscode](https://code.visualstudio.com/download)

#### Steps

Download the installation script docker-compose.yml

Run the installation script

```bash
chmod +x install.sh && ./install.sh
```

The script will download the Continue VSCode extension, create
a configuration file. The script will also create a docker-compose.yml file and start the services.

### Usage

Tap the Continue button in the VSCode editor to start the service
to bring up a chat window. The chat window will be displayed in the
VSCode editor.

![Continue Chat](./static/image.png)

## Usage

### Basic Usage (Manual)

Start the server with default settings:

```bash
codegate serve
```

### Custom Configuration

Start with custom settings:

```bash
codegate serve --port 8989 --host localhost --log-level DEBUG
```

### Configuration File

Use a YAML configuration file:

```bash
codegate serve --config my_config.yaml
```

Example `config.yaml`:

```yaml
port: 8989
host: "localhost"
log_level: "DEBUG"
```

### Environment Variables

Configure using environment variables:

```bash
export CODEGATE_APP_PORT=8989
export CODEGATE_APP_HOST=localhost
export CODEGATE_APP_LOG_LEVEL=DEBUG
codegate serve
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/stacklok/codegate.git
cd codegate

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Testing

```bash
pytest
```
