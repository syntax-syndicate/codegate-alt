<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./static/codegate-logo-white.svg">
  <img alt="CodeGate logo" src="./static/codegate-logo-dark.svg" width="800px" style="max-width: 100%;">
</picture>

---
[![CI](https://github.com/stacklok/codegate/actions/workflows/run-on-push.yml/badge.svg)](https://github.com/stacklok/codegate/actions/workflows/run-on-push.yml) | [![License: Apache 2.0](https://img.shields.io/badge/License-Apache2.0-brightgreen.svg)](https://opensource.org/licenses/Apache-2.0) | [![](https://dcbadge.vercel.app/api/server/RkzVuTp3WK?logo=discord&label=Discord&color=5865&style=flat)](https://discord.gg/RkzVuTp3WK) 

---
## Introduction

<img src="./assets/codegate.gif" style="width: 70%; height: 70%;" />

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

Check out the CodeGate **[website](https://codegate.ai)** and
**[documentation](https://docs.codegate.ai)** to learn more.

## Experimental 🚧

CodeGate is in active development and subject to **rapid change**.

- Features may change frequently
- Expect possible bugs and breaking changes
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

### Supported AI coding assistants and providers

CodeGate works with multiple development environments and AI providers.

- **[GitHub Copilot](https://github.com/features/copilot)** with Visual Studio
  Code and JetBrains IDEs

- **[Continue](https://www.continue.dev/)** with Visual Studio Code and
  JetBrains IDEs

With Continue, you can choose from several leading AI model providers:

- 💻 Local LLMs with [Ollama](https://ollama.com/) and
  [llama.cpp](https://github.com/ggerganov/llama.cpp) (run AI completely
  offline!)
- ⚡ [vLLM](https://docs.vllm.ai/en/latest/) (OpenAI-compatible mode, including
  OpenRouter)
- 🤖 [Anthropic API](https://www.anthropic.com/api)
- 🧠 [OpenAI API](https://openai.com/api/)

🔮 Many more on the way!

- **[Aider](https://aider.chat)**

With Aider, you can choose from two leading AI model providers:

- 💻 Local LLMs with [Ollama](https://ollama.com/)
- 🧠 [OpenAI API](https://openai.com/api/)


### Privacy first

Unlike E.T., your code never phones home! 🛸 CodeGate is designed with privacy
at its core:

- 🏠 Everything stays on your machine
- 🚫 No external data collection
- 🔐 No calling home or telemetry
- 💪 Complete control over your data

## 🚀 Quickstart

Check out the quickstart guides to get up and running quickly!

- [Quickstart guide for GitHub Copilot with VS Code](https://docs.codegate.ai/quickstart)
- [Quickstart guide for Continue with VS Code and Ollama](https://docs.codegate.ai/quickstart-continue)


## 🎯 Usage

### IDE integration

Simply open the Continue or Copilot chat in your IDE to start interacting with
your AI assistant - now protected by CodeGate!

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./static/continue-extension-dark.webp">
  <img alt="Continue chat in VS Code" src="./static/continue-extension-light.webp" width="720px" style="max-width: 100%;">
</picture>

Refer to the CodeGate docs for more information:

- [Using CodeGate](https://docs.codegate.ai/how-to)
- [CodeGate features](https://docs.codegate.ai/features)

## 🛠️ Development

Check out the developer reference guides:

- [Development guide](./docs/development.md)
- [CLI commands and flags](./docs/cli.md)
- [Configuration system](./docs/configuration.md)
- [Logging system](./docs/logging.md)

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

### Testing

To run the unit tests, execute this command:
```bash
pytest
```

To run the integration tests, create a `.env` file in the repo root directory and add the
following properties to it:
```
ENV_OPENAI_KEY=<YOUR_KEY>
ENV_VLLM_KEY=<YOUR_KEY>
ENV_ANTHROPIC_KEY=<YOUR_KEY>
```

Then the integration tests can be executed by running:
```bash
python tests/integration/integration_tests.py
```

## 🐳 Docker deployment

### Build the image

```bash
make image-build
```

### Run the container

```bash
# Basic usage with local image
docker run -p 8989:8989 -p 9090:9090 codegate:latest

# With pre-built pulled image
docker pull ghcr.io/stacklok/codegate:latest
docker run --name codegate -d -p 8989:8989 -p 9090:9090 ghcr.io/stacklok/codegate:latest

# It will mount a volume to /app/codegate_volume
# The directory supports storing Llama CPP models under subdirectory /models
# A sqlite DB with the messages and alerts is stored under the subdirectory /db
docker run --name codegate -d -v /path/to/volume:/app/codegate_volume -p 8989:8989 -p 9090:9090 ghcr.io/stacklok/codegate:latest
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
docker run -p 8989:8989 -p 9090:9090 -e CODEGATE_OLLAMA_URL=http://1.2.3.4:11434/api ghcr.io/stacklok/codegate:latest
```

## 🤝 Contributing

We welcome contributions! Whether it's bug reports, feature requests, or code
contributions, please feel free to contribute to making CodeGate better.

Start by reading the [Contributor Guidelines](./CONTRIBUTING.md).

## 📜 License

This project is licensed under the terms specified in the [LICENSE](LICENSE)
file.

<!-- markdownlint-disable-file first-line-heading no-inline-html -->
