import asyncio
import json
from typing import Optional

import httpx
from fastapi import Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from codegate.config import Config
from codegate.providers.base import BaseProvider, SequentialPipelineProcessor
from codegate.providers.litellmshim import LiteLLmShim, sse_stream_generator
from codegate.providers.ollama.adapter import OllamaInputNormalizer, OllamaOutputNormalizer


async def stream_ollama_response(client: httpx.AsyncClient, url: str, data: dict):
    """Stream response directly from Ollama API."""
    try:
        async with client.stream("POST", url, json=data, timeout=30.0) as response:
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


class OllamaProvider(BaseProvider):
    def __init__(
        self,
        pipeline_processor: Optional[SequentialPipelineProcessor] = None,
        fim_pipeline_processor: Optional[SequentialPipelineProcessor] = None,
    ):
        completion_handler = LiteLLmShim(stream_generator=sse_stream_generator)
        super().__init__(
            OllamaInputNormalizer(),
            OllamaOutputNormalizer(),
            completion_handler,
            pipeline_processor,
            fim_pipeline_processor,
        )
        self.client = httpx.AsyncClient(timeout=30.0)

    @property
    def provider_route_name(self) -> str:
        return "ollama"

    def _setup_routes(self):
        """
        Sets up Ollama API routes.
        """

        # Native Ollama API routes
        @self.router.post(f"/{self.provider_route_name}/api/chat")
        async def ollama_chat(
            request: Request,
            authorization: str = Header(..., description="Bearer token"),
        ):
            if not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Invalid authorization header")

            _api_key = authorization.split(" ")[1]
            body = await request.body()
            data = json.loads(body)

            # Get the Ollama base URL
            config = Config.get_config()
            base_url = config.provider_urls.get("ollama", "http://localhost:11434")

            # Convert chat format to Ollama generate format
            messages = []
            for msg in data.get("messages", []):
                role = msg.get("role", "")
                content = msg.get("content", "")
                if isinstance(content, list):
                    # Handle list-based content format
                    content = " ".join(
                        part["text"] for part in content if part.get("type") == "text"
                    )
                messages.append({"role": role, "content": content})

            ollama_data = {
                "model": data.get("model", "").strip(),
                "messages": messages,
                "stream": True,
                "options": data.get("options", {}),
            }

            # Stream response directly from Ollama
            return StreamingResponse(
                stream_ollama_response(self.client, f"{base_url}/api/chat", ollama_data),
                media_type="application/x-ndjson",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        @self.router.post(f"/{self.provider_route_name}/api/generate")
        async def ollama_generate(
            request: Request,
            authorization: str = Header(..., description="Bearer token"),
        ):
            if not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Invalid authorization header")

            _api_key = authorization.split(" ")[1]
            body = await request.body()
            data = json.loads(body)

            # Get the Ollama base URL
            config = Config.get_config()
            base_url = config.provider_urls.get("ollama", "http://localhost:11434")

            # Prepare generate request
            ollama_data = {
                "model": data.get("model", "").strip(),
                "prompt": data.get("prompt", ""),
                "stream": True,
                "options": data.get("options", {}),
            }

            # Add any context or system prompt if provided
            if "context" in data:
                ollama_data["context"] = data["context"]
            if "system" in data:
                ollama_data["system"] = data["system"]

            # Stream response directly from Ollama
            return StreamingResponse(
                stream_ollama_response(self.client, f"{base_url}/api/generate", ollama_data),
                media_type="application/x-ndjson",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        # OpenAI-compatible routes for backward compatibility
        @self.router.post(f"/{self.provider_route_name}/chat/completions")
        @self.router.post(f"/{self.provider_route_name}/completions")
        async def create_completion(
            request: Request,
            authorization: str = Header(..., description="Bearer token"),
        ):
            # Redirect to native Ollama endpoint
            return await ollama_chat(request, authorization)
