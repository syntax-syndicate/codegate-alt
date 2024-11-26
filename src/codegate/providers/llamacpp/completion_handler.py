from typing import Any, AsyncIterator, Dict

from litellm import ModelResponse
from fastapi.responses import StreamingResponse

from codegate.providers.base import BaseCompletionHandler
from codegate.providers.llamacpp.adapter import BaseAdapter
from codegate.inference.inference_engine import LlamaCppInferenceEngine
from codegate.config import Config


class LlamaCppCompletionHandler(BaseCompletionHandler):
    def __init__(self, adapter: BaseAdapter):
        self._config = Config.from_file('./config.yaml')
        self._adapter = adapter
        self.inference_engine = LlamaCppInferenceEngine()

    async def complete(self, data: Dict, api_key: str) -> AsyncIterator[Any]:
        """
        Translate the input parameters to LiteLLM's format using the adapter and
        call the LiteLLM API. Then translate the response back to our format using
        the adapter.
        """
        completion_request = self._adapter.translate_completion_input_params(
            data)
        if completion_request is None:
            raise Exception("Couldn't translate the request")

        # Replace n_predict option with max_tokens
        if 'n_predict' in completion_request:
            completion_request['max_tokens'] = completion_request['n_predict']
            del completion_request['n_predict']

        response = await self.inference_engine.chat(self._config.chat_model_path,
                                                    self._config.chat_model_n_ctx,
                                                    self._config.chat_model_n_gpu_layers,
                                                    **completion_request)

        if isinstance(response, ModelResponse):
            return self._adapter.translate_completion_output_params(response)
        return self._adapter.translate_completion_output_params_streaming(response)

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
