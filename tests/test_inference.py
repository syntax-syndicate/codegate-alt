
import pytest

# @pytest.mark.asyncio
# async def test_generate(inference_engine) -> None:
#     """Test code generation."""

#     prompt = '''
#         import requests

#         # Function to call API over http
#         def call_api(url):
#     '''
#     model_path = "./models/qwen2.5-coder-1.5B.q5_k_m.gguf"

#     async for chunk in inference_engine.generate(model_path, prompt):
#         print(chunk)


@pytest.mark.asyncio
async def test_chat(inference_engine) -> None:
    """Test chat completion."""
    pass

    # chat_request = {"prompt":
    #                 "<|im_start|>user\\nhello<|im_end|>\\n<|im_start|>assistant\\n",
    #                 "stream": True, "max_tokens": 4096, "top_k": 50, "temperature": 0}

    # model_path = "./models/qwen2.5-coder-1.5b-instruct-q5_k_m.gguf"
    # response = await inference_engine.chat(model_path, **chat_request)

    # for chunk in response:
    #     assert chunk['choices'][0]['text'] is not None


@pytest.mark.asyncio
async def test_embed(inference_engine) -> None:
    """Test content embedding."""
    pass

    # content = "Can I use invokehttp package in my project?"
    # model_path = "./models/all-minilm-L6-v2-q5_k_m.gguf"
    # vector = await inference_engine.embed(model_path, content=content)
    # assert len(vector) == 384
