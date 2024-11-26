from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Callable, Dict, Optional, Union

from fastapi import APIRouter
from litellm import ModelResponse

from codegate.providers.completion.base import BaseCompletionHandler
from codegate.providers.formatting.input_pipeline import PipelineResponseFormatter

from ..pipeline.base import SequentialPipelineProcessor

StreamGenerator = Callable[[AsyncIterator[Any]], AsyncIterator[str]]

class BaseProvider(ABC):
    """
    The provider class is responsible for defining the API routes and
    calling the completion method using the completion handler.
    """

    def __init__(
        self,
        completion_handler: BaseCompletionHandler,
        pipeline_processor: Optional[SequentialPipelineProcessor] = None
    ):
        self.router = APIRouter()
        self._completion_handler = completion_handler
        self._pipeline_processor = pipeline_processor
        self._pipeline_response_formatter = \
            PipelineResponseFormatter(completion_handler)
        self._setup_routes()

    @abstractmethod
    def _setup_routes(self) -> None:
        pass

    @property
    @abstractmethod
    def provider_route_name(self) -> str:
        pass

    async def complete(
            self, data: Dict, api_key: str,
        ) -> Union[ModelResponse, AsyncIterator[ModelResponse]]:
        """
        Main completion flow with pipeline integration

        The flow has three main steps:
        - Translate the request to the OpenAI API format used internally
        - Process the request with the pipeline processor. This can modify the request
          or yield a response. The response can either be returned or streamed back to
          the client
        - Execute the completion and translate the response back to the
          provider-specific format
        """
        completion_request = self._completion_handler.translate_request(data, api_key)
        streaming = data.get("stream", False)

        if self._pipeline_processor is not None:
            result = await self._pipeline_processor.process_request(completion_request)

            if result.error_message:
                raise Exception(result.error_message)

            if result.response:
                return self._pipeline_response_formatter.handle_pipeline_response(
                    result.response, streaming)

            completion_request = result.request

        # Execute the completion and translate the response
        # This gives us either a single response or a stream of responses
        # based on the streaming flag
        raw_response = await self._completion_handler.execute_completion(
            completion_request,
            stream=streaming
        )
        if not streaming:
            return self._completion_handler.translate_response(raw_response)
        return self._completion_handler.translate_streaming_response(raw_response)

    def get_routes(self) -> APIRouter:
        return self.router
