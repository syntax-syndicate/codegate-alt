import json

from fastapi import Request

from codegate.providers.base import BaseProvider
from codegate.providers.llamacpp.completion_handler import LlamaCppCompletionHandler
from codegate.providers.llamacpp.adapter import LlamaCppAdapter


class LlamaCppProvider(BaseProvider):
    def __init__(self):
        adapter = LlamaCppAdapter()
        completion_handler = LlamaCppCompletionHandler(adapter)
        super().__init__(completion_handler)

    @property
    def provider_route_name(self) -> str:
        return "llamacpp"

    def _setup_routes(self):
        """
        Sets up the /chat route for the provider as expected by the
        Llama API. Extracts the API key from the "Authorization" header and
        passes it to the completion handler.
        """
        @self.router.post(f"/{self.provider_route_name}/completion")
        async def create_completion(
            request: Request,
        ):
            body = await request.body()
            data = json.loads(body)

            stream = await self.complete(data, None)
            return self._completion_handler.create_streaming_response(stream)
