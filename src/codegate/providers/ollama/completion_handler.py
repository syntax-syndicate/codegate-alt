import json
from typing import AsyncIterator, Optional, Union

import structlog
from fastapi.responses import JSONResponse, StreamingResponse
from litellm import ChatCompletionRequest
from ollama import AsyncClient, ChatResponse, GenerateResponse

from codegate.providers.base import BaseCompletionHandler

logger = structlog.get_logger("codegate")


async def ollama_stream_generator(
    stream: AsyncIterator[ChatResponse], is_cline_client: bool
) -> AsyncIterator[str]:
    """OpenAI-style SSE format"""
    try:
        async for chunk in stream:
            try:
                # TODO We should wire in the client info so we can respond with
                # the correct format and start to handle multiple clients
                # in a more robust way.
                if not is_cline_client:
                    yield f"{chunk.model_dump_json()}\n\n"
                else:
                    # First get the raw dict from the chunk
                    chunk_dict = chunk.model_dump()
                    # Create response dictionary in OpenAI-like format
                    response = {
                        "id": f"chatcmpl-{chunk_dict.get('created_at', '')}",
                        "object": "chat.completion.chunk",
                        "created": chunk_dict.get("created_at"),
                        "model": chunk_dict.get("model"),
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "content": chunk_dict.get("message", {}).get("content", ""),
                                    "role": chunk_dict.get("message", {}).get("role", "assistant"),
                                },
                                "finish_reason": (
                                    chunk_dict.get("done_reason")
                                    if chunk_dict.get("done", False)
                                    else None
                                ),
                            }
                        ],
                    }
                    # Preserve existing type or add default if missing
                    response["type"] = chunk_dict.get("type", "stream")

                    # Add optional fields that might be present in the final message
                    optional_fields = [
                        "total_duration",
                        "load_duration",
                        "prompt_eval_count",
                        "prompt_eval_duration",
                        "eval_count",
                        "eval_duration",
                    ]
                    for field in optional_fields:
                        if field in chunk_dict:
                            response[field] = chunk_dict[field]

                    yield f"data: {json.dumps(response)}\n\n"
            except Exception as e:
                logger.error(f"Error in stream generator: {str(e)}")
                yield f"data: {json.dumps({'error': str(e), 'type': 'error', 'choices': []})}\n\n"
    except Exception as e:
        logger.error(f"Stream error: {str(e)}")
        yield f"data: {json.dumps({'error': str(e), 'type': 'error', 'choices': []})}\n\n"


class OllamaShim(BaseCompletionHandler):

    def __init__(self, base_url):
        self.client = AsyncClient(host=base_url, timeout=300)
        self.is_cline_client = False

    async def execute_completion(
        self,
        request: ChatCompletionRequest,
        api_key: Optional[str],
        stream: bool = False,
        is_fim_request: bool = False,
        is_cline_client: bool = False,
    ) -> Union[ChatResponse, GenerateResponse]:
        """Stream response directly from Ollama API."""

        # TODO: I don't like this, but it's a quick fix for now until we start
        # passing through the client info so we can respond with the correct
        # format.
        # Determine if the client is a Cline client
        self.is_cline_client = any(
            "Cline" in message["content"] for message in request.get("messages", [])
        )

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
            ollama_stream_generator(stream, self.is_cline_client),
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
