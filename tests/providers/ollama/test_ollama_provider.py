"""Tests for Ollama provider."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from codegate.providers.ollama.provider import OllamaProvider


class MockConfig:
    def __init__(self):
        self.provider_urls = {"ollama": "http://localhost:11434"}


@pytest.fixture
def app():
    """Create FastAPI app with Ollama provider."""
    app = FastAPI()
    provider = OllamaProvider()
    app.include_router(provider.get_routes())
    return app


@pytest.fixture
def test_client(app):
    """Create test client."""
    return TestClient(app)


async def async_iter(items):
    """Helper to create async iterator."""
    for item in items:
        yield item


@patch("codegate.config.Config.get_config", return_value=MockConfig())
def test_ollama_chat(mock_config, test_client):
    """Test chat endpoint."""
    data = {
        "model": "codellama:7b-instruct",
        "messages": [{"role": "user", "content": "Hello"}],
        "options": {"temperature": 0.7},
    }

    with patch("httpx.AsyncClient.stream") as mock_stream:
        # Mock the streaming response
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.aiter_lines = AsyncMock(
            return_value=async_iter(
                [
                    '{"response": "Hello!", "done": false}',
                    '{"response": " How can I help?", "done": true}',
                ]
            )
        )
        mock_stream.return_value.__aenter__.return_value = mock_response

        response = test_client.post(
            "/ollama/api/chat", json=data, headers={"Authorization": "Bearer test-key"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"

        # Verify the request to Ollama
        mock_stream.assert_called_once()
        call_args = mock_stream.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1].endswith("/api/chat")
        sent_data = call_args[1]["json"]
        assert sent_data["model"] == "codellama:7b-instruct"
        assert sent_data["messages"] == data["messages"]
        assert sent_data["options"] == data["options"]
        assert sent_data["stream"] is True


@patch("codegate.config.Config.get_config", return_value=MockConfig())
def test_ollama_generate(mock_config, test_client):
    """Test generate endpoint."""
    data = {
        "model": "codellama:7b-instruct",
        "prompt": "def hello_world",
        "options": {"temperature": 0.7},
        "context": [1, 2, 3],
        "system": "You are a helpful assistant",
    }

    with patch("httpx.AsyncClient.stream") as mock_stream:
        # Mock the streaming response
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.aiter_lines = AsyncMock(
            return_value=async_iter(
                [
                    '{"response": "():\\n", "done": false}',
                    '{"response": "    print(\\"Hello, World!\\")", "done": true}',
                ]
            )
        )
        mock_stream.return_value.__aenter__.return_value = mock_response

        response = test_client.post(
            "/ollama/api/generate", json=data, headers={"Authorization": "Bearer test-key"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"

        # Verify the request to Ollama
        mock_stream.assert_called_once()
        call_args = mock_stream.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1].endswith("/api/generate")
        sent_data = call_args[1]["json"]
        assert sent_data["model"] == "codellama:7b-instruct"
        assert sent_data["prompt"] == "def hello_world"
        assert sent_data["options"] == data["options"]
        assert sent_data["context"] == data["context"]
        assert sent_data["system"] == data["system"]
        assert sent_data["stream"] is True


@patch("codegate.config.Config.get_config", return_value=MockConfig())
def test_ollama_error_handling(mock_config, test_client):
    """Test error handling."""
    data = {"model": "invalid-model"}

    with patch("httpx.AsyncClient.stream") as mock_stream:
        # Mock an error response
        mock_stream.side_effect = Exception("Model not found")

        response = test_client.post(
            "/ollama/api/generate", json=data, headers={"Authorization": "Bearer test-key"}
        )

        assert response.status_code == 200  # Errors are returned in the stream
        content = response.content.decode().strip()
        assert "error" in content
        assert "Model not found" in content


def test_ollama_auth_required(test_client):
    """Test authentication requirement."""
    data = {"model": "codellama:7b-instruct"}

    # Test without auth header
    response = test_client.post("/ollama/api/generate", json=data)
    assert response.status_code == 422

    # Test with invalid auth header
    response = test_client.post(
        "/ollama/api/generate", json=data, headers={"Authorization": "Invalid"}
    )
    assert response.status_code == 401
