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
        # Make a copy of the data to avoid modifying the original
        normalized_data = data.copy()

        # Format the model name
        if "model" in normalized_data:
            normalized_data["model"] = normalized_data["model"].strip()

        # Convert messages format if needed
        if "messages" in normalized_data:
            messages = normalized_data["messages"]
            converted_messages = []
            for msg in messages:
                if isinstance(msg.get("content"), list):
                    # Convert list format to string
                    content_parts = []
                    for part in msg["content"]:
                        if part.get("type") == "text":
                            content_parts.append(part["text"])
                    msg = msg.copy()
                    msg["content"] = " ".join(content_parts)
                converted_messages.append(msg)
            normalized_data["messages"] = converted_messages

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
