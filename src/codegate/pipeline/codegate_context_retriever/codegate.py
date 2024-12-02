from typing import Optional

from litellm import ChatCompletionRequest, ChatCompletionSystemMessage

from codegate.pipeline.base import (
    PipelineContext,
    PipelineResult,
    PipelineStep,
)
from src.codegate.storage.storage_engine import StorageEngine
from src.codegate.utils.utils import generate_vector_string


class CodegateContextRetriever(PipelineStep):
    """
    Pipeline step that adds a context message to the completion request when it detects
    the word "codegate" in the user message.
    """

    def __init__(self, system_prompt_message: Optional[str] = None):
        self._system_message = ChatCompletionSystemMessage(
            content=system_prompt_message, role="system"
        )
        self.storage_engine = StorageEngine()

    @property
    def name(self) -> str:
        """
        Returns the name of this pipeline step.
        """
        return "codegate-context-retriever"

    async def get_objects_from_search(self, search: str) -> list[object]:
        objects = await self.storage_engine.search(search, distance=0.5)
        return objects

    def generate_context_str(self, objects: list[object]) -> str:
        context_str = ""
        for obj in objects:
            # generate dictionary from object
            package_obj = {
                "name": obj.properties["name"],
                "type": obj.properties["type"],
                "status": obj.properties["status"],
                "description": obj.properties["description"],
            }
            package_str = generate_vector_string(package_obj)
            context_str += package_str + "\n"
        return context_str

    async def process(
        self, request: ChatCompletionRequest, context: PipelineContext
    ) -> PipelineResult:
        """
        Process the completion request and add a system prompt if the user message contains
        the word "codegate".
        """
        # no prompt configured
        if not self._system_message["content"]:
            return PipelineResult(request=request)

        last_user_message = self.get_last_user_message(request)

        if last_user_message is not None:
            last_user_message_str, last_user_idx = last_user_message
            if last_user_message_str.lower():
                # Look for matches in vector DB
                searched_objects = await self.get_objects_from_search(last_user_message_str)

                # If matches are found, add the matched content to context
                if len(searched_objects) > 0:
                    context_str = self.generate_context_str(searched_objects)

                    # Make a copy of the request
                    new_request = request.copy()

                    # Add the context to the last user message
                    # Format: "Context: {context_str} \n Query: {last user message conent}"
                    # Handle the two cases: (a) message content is str, (b)message content
                    # is list
                    message = new_request["messages"][last_user_idx]
                    if isinstance(message["content"], str):
                        message["content"] = (
                            f'Context: {context_str} \n\n Query: {message["content"]}'
                        )
                    elif isinstance(message["content"], (list, tuple)):
                        for item in message["content"]:
                            if isinstance(item, dict) and item.get("type") == "text":
                                item["text"] = f'Context: {context_str} \n\n Query: {item["text"]}'

                    return PipelineResult(
                        request=new_request,
                    )

        # Fall through
        return PipelineResult(request=request)
