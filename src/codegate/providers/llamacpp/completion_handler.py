from typing import Any, AsyncIterator, Dict, Union

from fastapi.responses import StreamingResponse
from litellm import ChatCompletionRequest, ModelResponse

from codegate.providers.base import BaseCompletionHandler
from codegate.providers.llamacpp.adapter import BaseAdapter
from codegate.inference.inference_engine import LlamaCppInferenceEngine
from codegate.config import Config


class LlamaCppCompletionHandler(BaseCompletionHandler):
    def __init__(self, adapter: BaseAdapter):
        self._adapter = adapter
        self.inference_engine = LlamaCppInferenceEngine()

    def translate_request(self, data: Dict, api_key: str) -> ChatCompletionRequest:
        completion_request = self._adapter.translate_completion_input_params(
            data)
        if completion_request is None:
            raise Exception("Couldn't translate the request")

        return ChatCompletionRequest(**completion_request)

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
        Execute the completion request with inference engine API
        """
        model_path = f"{Config.get_config().model_base_path}/{request['model']}.gguf"

        if 'prompt' in request:
            response = await self.inference_engine.complete(model_path,
                                                        Config.get_config().chat_model_n_ctx,
                                                        Config.get_config().chat_model_n_gpu_layers,
                                                        **request)
        else:
            response = await self.inference_engine.chat(model_path,
                                                        Config.get_config().chat_model_n_ctx,
                                                        Config.get_config().chat_model_n_gpu_layers,
                                                        **request)
        return response

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
