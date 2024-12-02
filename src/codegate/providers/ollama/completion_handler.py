import asyncio
import json
from typing import Any, AsyncIterator, Optional

import httpx
import structlog
from fastapi.responses import JSONResponse, StreamingResponse
from litellm import ChatCompletionRequest

from codegate.providers.base import BaseCompletionHandler

logger = structlog.get_logger("codegate")


async def get_async_ollama_response(client, request_url, data):
    try:
        async with client.stream("POST", request_url, json=data, timeout=30.0) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        # Parse the response to ensure it's valid JSON
                        response_data = json.loads(line)
                        # Add newline to ensure proper streaming
                        yield line.encode("utf-8") + b"\n"
                        # If this is the final response, break
                        if response_data.get("done", False):
                            break
                        # Small delay to prevent overwhelming the client
                        await asyncio.sleep(0.01)
                    except json.JSONDecodeError:
                        yield json.dumps({"error": "Invalid JSON response"}).encode("utf-8") + b"\n"
                        break
                    except Exception as e:
                        yield json.dumps({"error": str(e)}).encode("utf-8") + b"\n"
                        break
    except Exception as e:
        yield json.dumps({"error": f"Stream error: {str(e)}"}).encode("utf-8") + b"\n"


class OllamaCompletionHandler(BaseCompletionHandler):
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        # Depends if the request is Chat or FIM
        self._url_mapping = {False: "/chat", True: "/generate"}

    async def execute_completion(
        self,
        request: ChatCompletionRequest,
        api_key: Optional[str],
        stream: bool = False,
        is_fim_request: bool = False,
    ) -> AsyncIterator:
        """Stream response directly from Ollama API."""
        request_path = self._url_mapping[is_fim_request]
        request_url = f"{request['base_url']}{request_path}"
        return get_async_ollama_response(self.client, request_url, request)

    def _create_streaming_response(self, stream: AsyncIterator[Any]) -> StreamingResponse:
        """
        Create a streaming response from a stream generator. The StreamingResponse
        is the format that FastAPI expects for streaming responses.
        """
        return StreamingResponse(
            stream,
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    def _create_json_response(self, response: Any) -> JSONResponse:
        raise NotImplementedError("JSON Reponse in Ollama not implemented yet.")
