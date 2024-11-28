# Codegate

[![CI](https://github.com/stacklok/codegate/actions/workflows/ci.yml/badge.svg)](https://github.com/stacklok/codegate/actions/workflows/ci.yml)

Codegate is a local gateway that makes AI coding assistants safer. Acting as a security checkpoint, Codegate ensures AI-generated recommendations adhere to best practices, while safeguarding your code's integrity, and protecting your individual privacy. With Codegate, you can confidently leverage AI in your development workflow without compromising security or control.

## ✨ Why Codegate?

In today's world where AI coding assistants are becoming ubiquitous, security can't be an afterthought. Codegate sits between you and AI, actively protecting your development process by:

- 🔒 Preventing accidental exposure of secrets and sensitive data
- 🛡️ Ensuring AI suggestions follow secure coding practices
- ⚠️ Blocking recommendations of known malicious or deprecated libraries
- 🔍 Providing real-time security analysis of AI suggestions

## 🌟 Features

### Supported AI Providers
Codegate works seamlessly with leading AI providers:
- 🤖 Anthropic (Claude)
- 🧠 OpenAI
- ⚡ vLLM
- 💻 Local LLMs (run AI completely offline!)
- 🔮 Many more on the way!

### Run AI Your Way
- 🌐 Cloud Providers: Use leading AI services like OpenAI and Anthropic
- 🏠 Local LLMs: Keep everything offline with local model support
- 🔄 Hybrid Mode: Mix and match cloud and local providers as needed

### AI Coding Assistants
We're starting with Continue VSCode extension support, with many more AI coding assistants coming soon!

### Privacy First
Unlike E.T., your code never phones home! 🛸 Codegate is designed with privacy at its core:
- 🏠 Everything stays on your machine
- 🚫 No external data collection
- 🔐 No calling home or telemetry
- 💪 Complete control over your data

## 🚀 Quick Start

### Prerequisites

Make sure you have these tools installed:

- 🐳 [Docker](https://docs.docker.com/get-docker/)
- 🔧 [Docker Compose](https://docs.docker.com/compose/install/)
- 🛠️ [jq](https://stedolan.github.io/jq/download/)
- 💻 [VSCode](https://code.visualstudio.com/download)

### One-Command Setup

```bash
chmod +x install.sh && ./install.sh
```

This script will:
1. Install the Continue VSCode extension
2. Set up your configuration
3. Create and start necessary Docker services

## 🎯 Usage

### VSCode Integration with Continue 

Simply tap the Continue button in your VSCode editor to start chatting with your AI assistant - now protected by Codegate!

![Continue Chat Interface](./static/image.png)

### Manual Configuration

#### Basic Server Start
```bash
codegate serve
```

#### Custom Settings
```bash
codegate serve --port 8989 --host localhost --log-level DEBUG
```

#### Using Config File
Create a `config.yaml`:
```yaml
port: 8989
host: "localhost"
log_level: "DEBUG"
```

Then run:
```bash
codegate serve --config config.yaml
```

#### Environment Variables
```bash
export CODEGATE_APP_PORT=8989
export CODEGATE_APP_HOST=localhost
export CODEGATE_APP_LOG_LEVEL=DEBUG
codegate serve
```

## 🛠️ Development

### Local Setup
```bash
# Get the code
git clone https://github.com/stacklok/codegate.git
cd codegate

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dev dependencies
pip install -e ".[dev]"
```

### Testing
```bash
pytest
```

## 🐳 Docker Deployment

### Build the Image
```bash
make image-build
```

### Run the Container
```bash
# Basic usage
docker run -p 8989:8989 codegate:latest

# With persistent data
docker run -p 8989:8989 -v /path/to/volume:/app/weaviate_data codegate:latest
```

## 🤝 Contributing

We welcome contributions! Whether it's bug reports, feature requests, or code contributions, please feel free to contribute to making Codegate better.

## 📜 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.
