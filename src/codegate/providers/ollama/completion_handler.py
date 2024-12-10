from typing import AsyncIterator, Optional, Union

import structlog
from fastapi.responses import JSONResponse, StreamingResponse
from litellm import ChatCompletionRequest
from ollama import AsyncClient, ChatResponse, GenerateResponse

from codegate.config import Config
from codegate.providers.base import BaseCompletionHandler

logger = structlog.get_logger("codegate")


async def ollama_stream_generator(
    stream: AsyncIterator[ChatResponse],
) -> AsyncIterator[str]:
    """OpenAI-style SSE format"""
    try:
        async for chunk in stream:
            try:
                yield f"{chunk.model_dump_json()}\n\n"
            except Exception as e:
                yield f"{str(e)}\n\n"
    except Exception as e:
        yield f"{str(e)}\n\n"


class OllamaShim(BaseCompletionHandler):

    def __init__(self):
        config = Config.get_config()
        if config is None:
            provided_urls = {}
        else:
            provided_urls = config.provider_urls
        base_url = provided_urls.get("ollama", "http://localhost:11434/")
        self.client = AsyncClient(host=base_url, timeout=300)

    async def execute_completion(
        self,
        request: ChatCompletionRequest,
        api_key: Optional[str],
        stream: bool = False,
        is_fim_request: bool = False,
    ) -> Union[ChatResponse, GenerateResponse]:
        """Stream response directly from Ollama API."""
        if is_fim_request:
            prompt = request["messages"][0]["content"]
            response = await self.client.generate(
                model=request["model"], prompt=prompt, stream=stream, options=request["options"]
            )
        else:
            response = await self.client.chat(
                model=request["model"],
                messages=request["messages"],
                stream=stream,
                options=request["options"],
            )
        return response

    def _create_streaming_response(self, stream: AsyncIterator[ChatResponse]) -> StreamingResponse:
        """
        Create a streaming response from a stream generator. The StreamingResponse
        is the format that FastAPI expects for streaming responses.
        """
        return StreamingResponse(
            ollama_stream_generator(stream),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    def _create_json_response(
        self, response: Union[GenerateResponse, ChatResponse]
    ) -> JSONResponse:
        return JSONResponse(content=response.model_dump_json(), status_code=200)
