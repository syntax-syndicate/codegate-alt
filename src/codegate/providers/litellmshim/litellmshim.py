from typing import Any, AsyncIterator, Dict, Union

from fastapi.responses import StreamingResponse
from litellm import ChatCompletionRequest, ModelResponse, acompletion

from codegate.providers.base import BaseCompletionHandler
from codegate.providers.litellmshim.adapter import BaseAdapter


class LiteLLmShim(BaseCompletionHandler):
    """
    LiteLLM Shim is a wrapper around LiteLLM's API that allows us to use it with
    our own completion handler interface without exposing the underlying
    LiteLLM API.
    """

    def __init__(self, adapter: BaseAdapter, completion_func=acompletion):
        self._adapter = adapter
        self._completion_func = completion_func

    def translate_request(self, data: Dict, api_key: str) -> ChatCompletionRequest:
        """
        Uses the configured adapter to translate the request data from the native
        LLM API format to the OpenAI API format used by LiteLLM internally.

        The OpenAPI format is also what our pipeline expects.
        """
        data["api_key"] = api_key
        completion_request = self._adapter.translate_completion_input_params(data)
        if completion_request is None:
            raise Exception("Couldn't translate the request")
        return completion_request

    def translate_streaming_response(
            self,
            response: AsyncIterator[ModelResponse],
    ) -> AsyncIterator[ModelResponse]:
        """
        Convert pipeline or completion response to provider-specific stream
        """
        return self._adapter.translate_completion_output_params_streaming(response)

    def translate_response(
            self,
            response: ModelResponse,
    ) -> ModelResponse:
        """
        Convert pipeline or completion response to provider-specific format
        """
        return self._adapter.translate_completion_output_params(response)

    async def execute_completion(
        self,
        request: ChatCompletionRequest,
        stream: bool = False
    ) -> Union[ModelResponse, AsyncIterator[ModelResponse]]:
        """
        Execute the completion request with LiteLLM's API
        """
        return await self._completion_func(**request)

    def create_streaming_response(
        self, stream: AsyncIterator[Any]
    ) -> StreamingResponse:
        """
        Create a streaming response from a stream generator. The StreamingResponse
        is the format that FastAPI expects for streaming responses.
        """
        return StreamingResponse(
            self._adapter.stream_generator(stream),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Transfer-Encoding": "chunked",
            },
            status_code=200,
        )
