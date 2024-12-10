"""Tests for Ollama adapter."""

from codegate.providers.ollama.adapter import OllamaInputNormalizer, OllamaOutputNormalizer


def test_normalize_ollama_input():
    """Test input normalization for Ollama."""
    normalizer = OllamaInputNormalizer()

    # Test model name handling
    data = {"model": "llama2"}
    normalized = normalizer.normalize(data)
    assert type(normalized) == dict  # noqa: E721
    assert normalized["model"] == "llama2"  # No prefix needed for Ollama

    # Test model name with spaces
    data = {"model": "codellama:7b-instruct "}  # Extra space
    normalized = normalizer.normalize(data)
    assert normalized["model"] == "codellama:7b-instruct"  # Space removed


def test_normalize_native_ollama_input():
    """Test input normalization for native Ollama API requests."""
    normalizer = OllamaInputNormalizer()

    # Test native Ollama request format
    data = {
        "model": "codellama:7b-instruct",
        "messages": [{"role": "user", "content": "Hello"}],
        "options": {"num_ctx": 8096, "num_predict": 6},
    }
    normalized = normalizer.normalize(data)
    assert type(normalized) == dict  # noqa: E721
    assert normalized["model"] == "codellama:7b-instruct"
    assert "options" in normalized
    assert normalized["options"]["num_ctx"] == 8096

    # Test native Ollama request with base URL
    data = {
        "model": "codellama:7b-instruct",
        "messages": [{"role": "user", "content": "Hello"}],
        "options": {"num_ctx": 8096, "num_predict": 6},
        "base_url": "http://localhost:11434",
    }
    normalized = normalizer.normalize(data)


def test_normalize_ollama_message_format():
    """Test normalization of Ollama message formats."""
    normalizer = OllamaInputNormalizer()

    # Test list-based content format
    data = {
        "model": "codellama:7b-instruct",
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}, {"type": "text", "text": "world"}],
            }
        ],
    }
    normalized = normalizer.normalize(data)
    assert normalized["messages"][0]["content"] == "Hello world"

    # Test mixed content format
    data = {
        "model": "codellama:7b-instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "other", "text": "ignored"},
                    {"type": "text", "text": "world"},
                ],
            }
        ],
    }
    normalized = normalizer.normalize(data)
    assert normalized["messages"][0]["content"] == "Hello world"


def test_normalize_ollama_generate_format():
    """Test normalization of Ollama generate format."""
    normalizer = OllamaInputNormalizer()

    # Test basic generate request
    data = {
        "model": "codellama:7b-instruct",
        "prompt": "def hello_world",
        "options": {"temperature": 0.7},
    }
    normalized = normalizer.normalize(data)
    assert normalized["model"] == "codellama:7b-instruct"
    assert normalized["messages"][0]["content"] == "def hello_world"
    assert normalized["options"]["temperature"] == 0.7

    # Test generate request with context
    data = {
        "model": "codellama:7b-instruct",
        "prompt": "def hello_world",
        "context": [1, 2, 3],
        "system": "You are a helpful assistant",
        "options": {"temperature": 0.7},
    }
    normalized = normalizer.normalize(data)
    assert normalized["context"] == [1, 2, 3]
    assert normalized["system"] == "You are a helpful assistant"


def test_normalize_ollama_output():
    """Test output normalization for Ollama."""
    normalizer = OllamaOutputNormalizer()

    # Test regular response passthrough
    response = {"message": {"role": "assistant", "content": "test"}}
    normalized = normalizer.normalize(response)
    assert normalized == response

    # Test generate response passthrough
    response = {"response": "def hello_world():", "done": False}
    normalized = normalizer.normalize(response)
    assert normalized == response

    # Test denormalize passthrough
    response = {"message": {"role": "assistant", "content": "test"}}
    denormalized = normalizer.denormalize(response)
    assert denormalized == response
