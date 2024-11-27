from litellm import ChatCompletionRequest

from codegate.pipeline.base import PipelineContext, PipelineResponse, PipelineResult, PipelineStep


class SecretAnalyzer(PipelineStep):
    """Pipeline step that handles version information requests."""

    message_blocked = """
        ⚠️ CodeGate Security Warning! Analysis Report ⚠️
        Potential leak of sensitive credentials blocked

        Recommendations:
        - Use environment variables for secrets
    """

    @property
    def name(self) -> str:
        """
        Returns the name of this pipeline step.

        Returns:
            str: The identifier 'fim-secret-analyzer'
        """
        return "fim-secret-analyzer"

    async def process(
            self,
            request: ChatCompletionRequest,
            context: PipelineContext
    ) -> PipelineResult:
        # We should call here Secrets Blocking module to see if the request messages contain secrets
        # messages_contain_secrets = [analyze_msg_secrets(msg) for msg in request.messages]
        # message_with_secrets = any(messages_contain_secretes)

        # For the moment to test shortcutting just treat all messages as if they contain secrets
        message_with_secrets = True
        if message_with_secrets:
            return PipelineResult(
                response=PipelineResponse(
                    step_name=self.name,
                    content=self.message_blocked,
                    model=request["model"],
                ),
            )

        # No messages with secrets, execute the rest of the pipeline
        return PipelineResult(request=request)
