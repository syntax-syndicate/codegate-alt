from typing import Any, Dict

from litellm import ChatCompletionRequest

from codegate.providers.normalizer.base import ModelInputNormalizer, ModelOutputNormalizer


class VLLMInputNormalizer(ModelInputNormalizer):
    def __init__(self):
        super().__init__()

    def normalize(self, data: Dict) -> ChatCompletionRequest:
        """
        Normalize the input data to the format expected by LiteLLM.
        Ensures the model name has the hosted_vllm prefix and base_url has /v1.
        """
        # Make a copy of the data to avoid modifying the original
        normalized_data = data.copy()

        # Format the model name to include the provider
        if "model" in normalized_data:
            model_name = normalized_data["model"]
            if not model_name.startswith("hosted_vllm/"):
                normalized_data["model"] = f"hosted_vllm/{model_name}"

        # Ensure the base_url ends with /v1 if provided
        if "base_url" in normalized_data:
            base_url = normalized_data["base_url"].rstrip("/")
            if not base_url.endswith("/v1"):
                normalized_data["base_url"] = f"{base_url}/v1"

        return ChatCompletionRequest(**normalized_data)

    def denormalize(self, data: ChatCompletionRequest) -> Dict:
        """
        Convert back to raw format for the API request
        """
        return data


class VLLMOutputNormalizer(ModelOutputNormalizer):
    def __init__(self):
        super().__init__()

    def normalize_streaming(
        self,
        model_reply: Any,
    ) -> Any:
        """
        No normalizing needed for streaming responses
        """
        return model_reply

    def normalize(self, model_reply: Any) -> Any:
        """
        No normalizing needed for responses
        """
        return model_reply

    def denormalize(self, normalized_reply: Any) -> Any:
        """
        No denormalizing needed for responses
        """
        return normalized_reply

    def denormalize_streaming(
        self,
        normalized_reply: Any,
    ) -> Any:
        """
        No denormalizing needed for streaming responses
        """
        return normalized_reply
