import pytest


@pytest.mark.asyncio
async def test_generate(inference_engine) -> None:
    """Test code generation."""

    completion_request = {
        "model": "qwen2.5-coder-1.5b-instruct-q5_k_m",
        "max_tokens": 4096,
        "temperature": 0,
        "stream": True,
        "stop": [
            "<|endoftext|>",
            "<|fim_prefix|>",
            "<|fim_middle|>",
            "<|fim_suffix|>",
            "<|fim_pad|>",
            "<|repo_name|>",
            "<|file_sep|>",
            "<|im_start|>",
            "<|im_end|>",
            "/src/",
            "#- coding: utf-8",
            "```",
        ],
        "prompt": "<|fim_prefix|>\\n# codegate/test.py\\nimport requests\\n\\ndef call_api(url):\\n"
        "    <|fim_suffix|>\\n\\n\\n\\nresponse = call_api('http://localhost/test')"
        "\\nprint(response)<|fim_middle|>",
    }
    model_path = f"./models/{completion_request['model']}.gguf"
    response = await inference_engine.complete(model_path, **completion_request)

    for chunk in response:
        assert chunk["choices"][0]["text"] is not None


@pytest.mark.asyncio
async def test_chat(inference_engine) -> None:
    """Test chat completion."""

    chat_request = {
        "messages": [{"role": "user", "content": "hello"}],
        "model": "qwen2.5-coder-1.5b-instruct-q5_k_m",
        "max_tokens": 4096,
        "temperature": 0,
        "stream": True,
    }

    model_path = f"./models/{chat_request['model']}.gguf"
    response = await inference_engine.chat(model_path, **chat_request)

    for chunk in response:
        assert "delta" in chunk["choices"][0]


@pytest.mark.asyncio
async def test_embed(inference_engine) -> None:
    """Test content embedding."""

    content = "Can I use invokehttp package in my project?"
    model_path = "./models/all-minilm-L6-v2-q5_k_m.gguf"
    vector = await inference_engine.embed(model_path, content=content)
    assert len(vector) == 384
