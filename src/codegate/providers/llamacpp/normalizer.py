from typing import Any, AsyncIterable, AsyncIterator, Dict, Iterable, Iterator, Union

from litellm import ChatCompletionRequest, ModelResponse

from codegate.providers.normalizer import ModelInputNormalizer, ModelOutputNormalizer


class LLamaCppInputNormalizer(ModelInputNormalizer):
    def normalize(self, data: Dict) -> ChatCompletionRequest:
        """
        Normalize the input data
        """
        # When doing FIM, we receive "prompt" instead of messages. Normalizing.
        if "prompt" in data:
            data["messages"] = [{"content": data.pop("prompt"), "role": "user"}]
            # We can add as many parameters as we like to data. ChatCompletionRequest is not strict.
            data["had_prompt_before"] = True
        try:
            return ChatCompletionRequest(**data)
        except Exception as e:
            raise ValueError(f"Invalid completion parameters: {str(e)}")

    def denormalize(self, data: ChatCompletionRequest) -> Dict:
        """
        Denormalize the input data
        """
        # If we receive "prompt" in FIM, we need convert it back.
        if data.get("had_prompt_before", False):
            data["prompt"] = data["messages"][0]["content"]
            del data["had_prompt_before"]
            del data["messages"]
        return data


class LLamaCppOutputNormalizer(ModelOutputNormalizer):
    def normalize_streaming(
        self,
        model_reply: Union[AsyncIterable[Any], Iterable[Any]],
    ) -> Union[AsyncIterator[ModelResponse], Iterator[ModelResponse]]:
        """
        Normalize the output stream. This is a pass-through for liteLLM output normalizer
        as the liteLLM output is already in the normalized format.
        """
        return model_reply

    def normalize(self, model_reply: Any) -> ModelResponse:
        """
        Normalize the output data. This is a pass-through for liteLLM output normalizer
        as the liteLLM output is already in the normalized format.
        """
        return model_reply

    def denormalize(self, normalized_reply: ModelResponse) -> Any:
        """
        Denormalize the output data from the completion function to the format
        expected by the client
        """
        return normalized_reply

    def denormalize_streaming(
        self,
        normalized_reply: Union[AsyncIterable[ModelResponse], Iterable[ModelResponse]],
    ) -> Union[AsyncIterator[Any], Iterator[Any]]:
        """
        Denormalize the output stream from the completion function to the format
        expected by the client
        """
        return normalized_reply
