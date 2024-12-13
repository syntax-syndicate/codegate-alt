<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./static/codegate-logo-white.svg">
  <img alt="CodeGate logo" src="./static/codegate-logo-white.svg" width="800px" style="max-width: 100%;">
</picture>

[![CI](https://github.com/stacklok/codegate/actions/workflows/ci.yml/badge.svg)](https://github.com/stacklok/codegate/actions/workflows/ci.yml)

CodeGate is a local gateway that makes AI coding assistants safer. CodeGate
ensures AI-generated recommendations adhere to best practices, while
safeguarding your code's integrity, and protecting your individual privacy. With
CodeGate, you can confidently leverage AI in your development workflow without
compromising security or productivity. CodeGate is designed to work seamlessly
with coding assistants, allowing you to safely enjoy all the benefits of AI code
generation.

CodeGate is developed by [Stacklok](https://stacklok.com), a group of security
experts with many years of experience building developer friendly open source
security software tools and platforms.

## Experimental 🚧

CodeGate is **experimental** and **undergoing fast iterations of development**.

- Features may change frequently
- Expect possible bugs
- Contributions, feedback, and testing are highly encouraged and welcomed!

## ✨ Why CodeGate?

In today's world where AI coding assistants are becoming ubiquitous, security
can't be an afterthought. CodeGate sits between you and AI, actively protecting
your development process by:

- 🔒 Preventing accidental exposure of secrets and sensitive data
- 🛡️ Ensuring AI suggestions follow secure coding practices
- ⚠️ Blocking recommendations of known malicious or deprecated libraries
- 🔍 Providing real-time security analysis of AI suggestions

## 🌟 Features

### Supported AI providers

CodeGate works seamlessly with leading AI providers:

- 🤖 Anthropic (Claude)
- 🧠 OpenAI
- ⚡ vLLM
- 💻 Local LLMs (run AI completely offline!)
- 🔮 Many more on the way!

### AI coding assistants

We're starting with Continue VS Code extension support, with many more AI coding
assistants coming soon!

### Privacy first

Unlike E.T., your code never phones home! 🛸 CodeGate is designed with privacy
at its core:

- 🏠 Everything stays on your machine
- 🚫 No external data collection
- 🔐 No calling home or telemetry
- 💪 Complete control over your data

## 🚀 Quickstart

### Prerequisites

Make sure you have these tools installed:

- 🐳 [Docker](https://docs.docker.com/get-docker/)
- 🛠️ [jq](https://stedolan.github.io/jq/download/)
- 💻 [VS Code](https://code.visualstudio.com/download)

### One-command setup

```bash
chmod +x install.sh && ./install.sh
```

This script will:

1. Install the Continue VS Code extension
2. Set up your configuration
3. Create and start necessary Docker services

## 🎯 Usage

### VS Code integration with Continue

Simply tap the Continue button in your VS Code editor to start chatting with
your AI assistant - now protected by CodeGate!

![Continue chat interface](./static/image.png)

### Manual configuration

#### Basic server start

```bash
codegate serve
```

#### Custom settings

```bash
codegate serve --port 8989 --host localhost --log-level DEBUG
```

#### Using config file

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

#### Environment variables

```bash
export CODEGATE_APP_PORT=8989
export CODEGATE_APP_HOST=localhost
export CODEGATE_APP_LOG_LEVEL=DEBUG
codegate serve
```

## 🛠️ Development

### Local setup

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

### Running locally with several network interfaces

By default weaviate is picking the default route as the ip for the cluster
nodes. It may cause some issues when dealing with multiple interfaces. To make
it work, localhost needs to be the default route:

```bash
sudo route delete default
sudo route add default 127.0.0.1
sudo route add -net 0.0.0.0/1 <public_ip_gateway>
sudo route add -net 128.0.0.0/1 <public_ip_gateway>
```

### Testing

```bash
pytest
```

## 🐳 Docker deployment

### Build the image

```bash
make image-build
```

### Run the container

```bash
# Basic usage with local image
docker run -p 8989:8989 -p 9090:80 codegate:latest

# With pre-built pulled image
docker pull ghcr.io/stacklok/codegate:latest
docker run --name codegate -d -p 8989:8989 -p 9090:80 ghcr.io/stacklok/codegate:latest

# It will mount a volume to /app/codegate_volume
# The directory supports storing Llama CPP models under subidrectoy /models
# A sqlite DB with the messages and alerts is stored under the subdirectory /db
docker run --name codegate -d -v /path/to/volume:/app/codegate_volume -p 8989:8989 -p 9090:80 ghcr.io/stacklok/codegate:latest
```

### Exposed parameters

- CODEGATE_VLLM_URL: URL for the inference engine (defaults to
  [https://inference.codegate.ai](https://inference.codegate.ai))
- CODEGATE_OPENAI_URL: URL for OpenAI inference engine (defaults to
  [https://api.openai.com/v1](https://api.openai.com/v1))
- CODEGATE_ANTHROPIC_URL: URL for Anthropic inference engine (defaults to
  [https://api.anthropic.com/v1](https://api.anthropic.com/v1))
- CODEGATE_OLLAMA_URL: URL for OLlama inference engine (defaults to
  [http://localhost:11434/api](http://localhost:11434/api))
- CODEGATE_APP_LOG_LEVEL: Level of debug desired when running the codegate
  server (defaults to WARNING, can be ERROR/WARNING/INFO/DEBUG)
- CODEGATE_LOG_FORMAT: Type of log formatting desired when running the codegate
  server (default to TEXT, can be JSON/TEXT)

```bash
docker run -p 8989:8989 -p 9090:80 -e CODEGATE_OLLAMA_URL=http://1.2.3.4:11434/api ghcr.io/stacklok/codegate:latest
```

## 🤝 Contributing

We welcome contributions! Whether it's bug reports, feature requests, or code
contributions, please feel free to contribute to making CodeGate better.

## 📜 License

This project is licensed under the terms specified in the [LICENSE](LICENSE)
file.

<!-- markdownlint-disable-file first-line-heading no-inline-html -->
