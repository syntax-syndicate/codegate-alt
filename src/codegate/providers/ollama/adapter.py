from typing import Any, Dict

from litellm import ChatCompletionRequest

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
        normalized_data["options"] = data.get("options", {})

        # Add any context or system prompt if provided
        if "context" in data:
            normalized_data["context"] = data["context"]
        if "system" in data:
            normalized_data["system"] = data["system"]

        # Format the model name
        if "model" in normalized_data:
            normalized_data["model"] = data["model"].strip()

        # Ensure the base_url ends with /api if provided
        if "base_url" in normalized_data:
            base_url = normalized_data["base_url"].rstrip("/")
            if not base_url.endswith("/api"):
                normalized_data["base_url"] = f"{base_url}/api"

        return ChatCompletionRequest(**normalized_data)

    def denormalize(self, data: ChatCompletionRequest) -> Dict:
        """
        Convert back to raw format for the API request
        """
        return data


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
        return model_reply

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
        return normalized_reply
