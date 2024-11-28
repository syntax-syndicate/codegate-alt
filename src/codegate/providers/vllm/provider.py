import json
from typing import Optional

from fastapi import Header, HTTPException, Request

from codegate.config import Config
from codegate.providers.base import BaseProvider, SequentialPipelineProcessor
from codegate.providers.litellmshim import LiteLLmShim, sse_stream_generator
from codegate.providers.vllm.adapter import VLLMInputNormalizer, VLLMOutputNormalizer


class VLLMProvider(BaseProvider):
    def __init__(
        self,
        pipeline_processor: Optional[SequentialPipelineProcessor] = None,
        fim_pipeline_processor: Optional[SequentialPipelineProcessor] = None,
    ):
        completion_handler = LiteLLmShim(stream_generator=sse_stream_generator)
        super().__init__(
            VLLMInputNormalizer(),
            VLLMOutputNormalizer(),
            completion_handler,
            pipeline_processor,
            fim_pipeline_processor,
        )

    @property
    def provider_route_name(self) -> str:
        return "vllm"

    def _setup_routes(self):
        """
        Sets up the /chat/completions route for the provider as expected by the
        OpenAI API. Extracts the API key from the "Authorization" header and
        passes it to the completion handler.
        """

        @self.router.post(f"/{self.provider_route_name}/chat/completions")
        @self.router.post(f"/{self.provider_route_name}/completions")
        async def create_completion(
            request: Request,
            authorization: str = Header(..., description="Bearer token"),
        ):
            if not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Invalid authorization header")

            api_key = authorization.split(" ")[1]
            body = await request.body()
            data = json.loads(body)

            # Add the vLLM base URL to the request
            config = Config.get_config()
            data["base_url"] = config.provider_urls.get("vllm")

            is_fim_request = self._is_fim_request(request, data)
            stream = await self.complete(data, api_key, is_fim_request=is_fim_request)
            return self._completion_handler.create_streaming_response(stream)
