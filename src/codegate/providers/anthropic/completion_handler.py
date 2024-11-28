from typing import AsyncIterator, Optional, Union

from litellm import ChatCompletionRequest, ModelResponse

from codegate.providers.litellmshim import LiteLLmShim


class AnthropicCompletion(LiteLLmShim):
    """
    LiteLLM Shim is a wrapper around LiteLLM's API that allows us to use it with
    our own completion handler interface without exposing the underlying
    LiteLLM API.
    """

    async def execute_completion(
        self,
        request: ChatCompletionRequest,
        api_key: Optional[str],
        stream: bool = False,
    ) -> Union[ModelResponse, AsyncIterator[ModelResponse]]:
        """
        Execute the completion request with LiteLLM's API
        """
        model_in_request = request['model']
        if not model_in_request.startswith('anthropic/'):
            request['model'] = f'anthropic/{model_in_request}'
        return await super().execute_completion(request, api_key, stream)
