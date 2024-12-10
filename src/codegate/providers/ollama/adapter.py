import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Iterable

from litellm import ChatCompletionRequest, ModelResponse
from litellm.types.utils import Delta, StreamingChoices
from ollama import ChatResponse, Message

from codegate.providers.normalizer.base import ModelInputNormalizer, ModelOutputNormalizer


class OllamaInputNormalizer(ModelInputNormalizer):
    def __init__(self):
        super().__init__()

    def normalize(self, data: Dict) -> ChatCompletionRequest:
        """
        Normalize the input data to the format expected by Ollama.
        """
        # Make a copy of the data to avoid modifying the original and normalize the message content
        normalized_data = self._normalize_content_messages(data)
        normalized_data["model"] = data.get("model", "").strip()
        normalized_data["options"] = data.get("options", {})
        # In Ollama force the stream to be True. Continue is not setting this parameter and
        # most of our functionality is for streaming completions.
        normalized_data["stream"] = True

        return ChatCompletionRequest(**normalized_data)

    def denormalize(self, data: ChatCompletionRequest) -> Dict:
        """
        Convert back to raw format for the API request
        """
        return data


class OLlamaToModel(AsyncIterator[ModelResponse]):
    def __init__(self, ollama_response: Iterable[ChatResponse]):
        self.ollama_response = ollama_response
        self._iterator = iter(ollama_response)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            chunk = next(self._iterator)
            finish_reason = None
            role = "assistant"

            # Convert the datetime object to a timestamp in seconds
            datetime_obj = datetime.fromisoformat(chunk.created_at)
            timestamp_seconds = int(datetime_obj.timestamp())

            if chunk.done:
                finish_reason = "stop"
                role = None

            model_response = ModelResponse(
                id=f"ollama-chat-{str(uuid.uuid4())}",
                created=timestamp_seconds,
                model=chunk.model,
                object="chat.completion.chunk",
                choices=[
                    StreamingChoices(
                        finish_reason=finish_reason,
                        index=0,
                        delta=Delta(content=chunk.message.content, role=role),
                        logprobs=None,
                    )
                ],
            )
            return model_response
        except StopIteration:
            raise StopAsyncIteration


class ModelToOllama(AsyncIterator[ChatResponse]):

    def __init__(self, normalized_reply: AsyncIterator[ModelResponse]):
        self.normalized_reply = normalized_reply
        self._aiter = normalized_reply.__aiter__()

    def __aiter__(self):
        return self

    async def __anext__(self) -> ChatResponse:
        try:
            chunk = await self._aiter.__anext__()
            # Convert the timestamp to a datetime object
            datetime_obj = datetime.fromtimestamp(chunk.created, tz=timezone.utc)
            created_at = datetime_obj.isoformat()

            message = chunk.choices[0].delta.content
            done = False
            if chunk.choices[0].finish_reason == "stop":
                done = True
                message = ""

            # Convert the model response to an Ollama response
            ollama_response = ChatResponse(
                model=chunk.model,
                created_at=created_at,
                done=done,
                message=Message(content=message, role="assistant"),
            )

            return ollama_response
        except StopAsyncIteration:
            raise StopAsyncIteration


class OllamaOutputNormalizer(ModelOutputNormalizer):
    def __init__(self):
        super().__init__()

    def normalize_streaming(
        self,
        model_reply: Any,
    ) -> Any:
        """
        Pass through Ollama response
        """
        return OLlamaToModel(model_reply)

    def normalize(self, model_reply: Any) -> Any:
        """
        Pass through Ollama response
        """
        return model_reply

    def denormalize(self, normalized_reply: Any) -> Any:
        """
        Pass through Ollama response
        """
        return normalized_reply

    def denormalize_streaming(
        self,
        normalized_reply: Any,
    ) -> Any:
        """
        Pass through Ollama response
        """
        return ModelToOllama(normalized_reply)
