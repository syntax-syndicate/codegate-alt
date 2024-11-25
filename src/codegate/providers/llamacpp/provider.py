import json

from fastapi import Header, HTTPException, Request

from ..base import BaseProvider
from .completion_handler import LlamaCppCompletionHandler
from .adapter import LlamaCppAdapter


class LlamaCppProvider(BaseProvider):
    def __init__(self):
        adapter = LlamaCppAdapter()
        completion_handler = LlamaCppCompletionHandler(adapter)
        super().__init__(completion_handler)

    def _setup_routes(self):
        """
        Sets up the /chat route for the provider as expected by the
        Llama API. Extracts the API key from the "Authorization" header and
        passes it to the completion handler.
        """
        @self.router.post("/completion")
        async def create_completion(
            request: Request,
        ):
            body = await request.body()
            data = json.loads(body)

            stream = await self.complete(data, None)
            return self._completion_handler.create_streaming_response(stream)
