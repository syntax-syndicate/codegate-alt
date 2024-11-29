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
            content=system_prompt_message,
            role="system"
        )
        self.storage_engine = StorageEngine()

    @property
    def name(self) -> str:
        """
        Returns the name of this pipeline step.
        """
        return "codegate-context-retriever"

    async def get_objects_from_search(self, search: str) -> list[object]:
        objects = await self.storage_engine.search(search)
        return objects

    def generate_context_str(self, objects: list[object]) -> str:
        context_str = "Please use the information about related packages to influence your answer:\n"
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
            if "codegate" in last_user_message_str.lower():
                # strip codegate from prompt and trim it
                last_user_message_str = last_user_message_str.lower().replace("codegate", "").strip()
                searched_objects = await self.get_objects_from_search(last_user_message_str)
                context_str = self.generate_context_str(searched_objects)
                # Add a system prompt to the completion request
                new_request = request.copy()
                new_request["messages"].insert(last_user_idx, context_str)
                return PipelineResult(
                    request=new_request,
                )

        # Fall through
        return PipelineResult(request=request)
