from typing import Optional

from litellm import ChatCompletionRequest, ChatCompletionSystemMessage

from codegate.pipeline.base import (
    PipelineContext,
    PipelineResult,
    PipelineStep,
)


class SystemPrompt(PipelineStep):
    """
    Pipeline step that adds a system prompt to the completion request when it detects
    the word "codegate" in the user message.
    """

    def __init__(self, system_prompt: str):
        self._system_message = ChatCompletionSystemMessage(
            content=system_prompt, role="system"
        )

    @property
    def name(self) -> str:
        """
        Returns the name of this pipeline step.
        """
        return "system-prompt"

    async def process(
        self, request: ChatCompletionRequest, context: PipelineContext
    ) -> PipelineResult:
        """
        Add system prompt if not present, otherwise prepend codegate system prompt
        to the existing system prompt
        """
        new_request = request.copy()

        if "messages" not in new_request:
            new_request["messages"] = []

        request_system_message = None
        for message in new_request["messages"]:
            if message["role"] == "system":
                request_system_message = message

        if request_system_message is None:
            # Add system message
            new_request["messages"].insert(0, self._system_message)
        elif "codegate" not in request_system_message["content"].lower():
            # Prepend to the system message
            request_system_message["content"] = self._system_message["content"] + \
                "\n Here are additional instructions. \n " + request_system_message["content"]

        return PipelineResult(
            request=new_request,
        )
