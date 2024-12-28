from typing import AsyncIterator, Optional, Union

import structlog
from fastapi.responses import JSONResponse, StreamingResponse
from litellm import ChatCompletionRequest
from ollama import AsyncClient, ChatResponse, GenerateResponse
import json

from codegate.providers.base import BaseCompletionHandler

logger = structlog.get_logger("codegate")


async def ollama_stream_generator(
    stream: AsyncIterator[ChatResponse],
) -> AsyncIterator[str]:
    """OpenAI-style SSE format"""
    try:
        async for chunk in stream:
            try:
                # First get the raw dict from the chunk
                chunk_dict = chunk.model_dump()
                # Create response dictionary, preserving existing type if present
                response = {
                    "model": chunk_dict.get("model"),
                    "created_at": chunk_dict.get("created_at"),
                    "message": chunk_dict.get("message"),
                    "done": chunk_dict.get("done", False)
                }
                # Preserve existing type or add default if missing
                response["type"] = chunk_dict.get("type", "stream")
                
                # Add optional fields that might be present in the final message
                optional_fields = [
                    "done_reason", "total_duration", "load_duration",
                    "prompt_eval_count", "prompt_eval_duration",
                    "eval_count", "eval_duration"
                ]
                for field in optional_fields:
                    if field in chunk_dict:
                        response[field] = chunk_dict[field]
                
                yield f"data: {json.dumps(response)}\n\n"
            except Exception as e:
                logger.error(f"Error in stream generator: {str(e)}")
                yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
    except Exception as e:
        logger.error(f"Stream error: {str(e)}")
        yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"


class OllamaShim(BaseCompletionHandler):

    def __init__(self, base_url):
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
