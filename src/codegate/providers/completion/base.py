from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Union

from fastapi.responses import StreamingResponse
from litellm import ChatCompletionRequest, ModelResponse


class BaseCompletionHandler(ABC):
    """
    The completion handler is responsible for executing the completion request
    and creating the streaming response.
    """

    @abstractmethod
    def translate_request(self, data: Dict, api_key: str) -> ChatCompletionRequest:
        """Convert raw request data into a ChatCompletionRequest"""
        pass

    @abstractmethod
    async def execute_completion(
            self,
            request: ChatCompletionRequest,
            stream: bool = False
    ) -> Union[ModelResponse, AsyncIterator[ModelResponse]]:
        """Execute the completion request"""
        pass

    @abstractmethod
    def create_streaming_response(
            self, stream: AsyncIterator[Any]
    ) -> StreamingResponse:
        pass

    @abstractmethod
    def translate_response(
            self,
            response: ModelResponse,
    ) -> ModelResponse:
        """Convert pipeline response to provider-specific format"""
        pass

    @abstractmethod
    def translate_streaming_response(
            self,
            response: AsyncIterator[ModelResponse],
    ) -> AsyncIterator[ModelResponse]:
        """Convert pipeline response to provider-specific format"""
        pass

