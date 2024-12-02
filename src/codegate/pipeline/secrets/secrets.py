import structlog
from litellm import ChatCompletionRequest

from codegate.pipeline.base import (
    PipelineContext,
    PipelineResult,
    PipelineStep,
)
from codegate.pipeline.secrets.manager import SecretsManager
from codegate.pipeline.secrets.signatures import CodegateSignatures

logger = structlog.get_logger("codegate")


class CodegateSecrets(PipelineStep):
    """Pipeline step that handles secret information requests."""

    def __init__(self):
        """Initialize the CodegateSecrets pipeline step."""
        super().__init__()

    @property
    def name(self) -> str:
        """
        Returns the name of this pipeline step.

        Returns:
            str: The identifier 'codegate-secrets'.
        """
        return "codegate-secrets"

    def _get_absolute_position(self, line_number: int, line_offset: int, text: str) -> int:
        """
        Convert line number and offset to absolute position in text.

        Args:
            line_number: The line number (1-based)
            line_offset: The offset within the line
            text: The full text

        Returns:
            Absolute position in text
        """
        lines = text.split("\n")
        position = sum(len(line) + 1 for line in lines[: line_number - 1])
        return position + line_offset

    def _extend_match_boundaries(self, text: str, start: int, end: int) -> tuple[int, int]:
        """
        Extend match boundaries to include full token if partially matched.

        Args:
            text: The full text
            start: Starting position of match
            end: Ending position of match

        Returns:
            Tuple of (new_start, new_end)
        """

        # Search backwards for opening quote or start of string
        while start > 0 and text[start - 1] not in ['"', "'", " ", "\n", "="]:
            start -= 1

        # Search forwards for closing quote or end of string
        while end < len(text) and text[end] not in ['"', "'", " ", "\n"]:
            end += 1

        return start, end

    def _redeact_text(self, text: str, secrets_manager: SecretsManager, session_id: str) -> str:
        """
        Find and encrypt secrets in the given text.

        Args:
            text: The text to protect

        Returns:
            Protected text with encrypted values
        """
        # Find secrets in the text
        matches = CodegateSignatures.find_in_string(text)
        if not matches:
            return text

        logger.debug(f"Found {len(matches)} secrets in the user message")

        # Convert line positions to absolute positions and extend boundaries
        absolute_matches = []
        for match in matches:
            start = self._get_absolute_position(match.line_number, match.start_index, text)
            end = self._get_absolute_position(match.line_number, match.end_index, text)

            # Extend boundaries to include full token
            start, end = self._extend_match_boundaries(text, start, end)

            # Get the full value
            full_value = text[start:end]
            absolute_matches.append((start, end, match._replace(value=full_value)))

        # Sort matches in reverse order to replace from end to start
        absolute_matches.sort(key=lambda x: x[0], reverse=True)

        # Make a mutable copy of the text
        protected_text = list(text)

        # Store matches for logging
        found_secrets = []

        # Replace each match with its encrypted value
        for start, end, match in absolute_matches:
            # Encrypt and store the value
            encrypted_value = secrets_manager.store_secret(
                match.value,
                match.service,
                match.type,
                session_id,
            )

            # Create the replacement string
            replacement = f"REDACTED<${encrypted_value}>"

            # Replace the secret in the text
            protected_text[start:end] = replacement
            # Store for logging
            found_secrets.append(
                {
                    "service": match.service,
                    "type": match.type,
                    "original": match.value,
                    "encrypted": encrypted_value,
                }
            )

            # Convert back to string
            protected_string = "".join(protected_text)

            # Log the findings
            logger.info("\nFound secrets:")

            for secret in found_secrets:
                logger.info(f"\nService: {secret['service']}")
                logger.info(f"Type: {secret['type']}")
                logger.info(f"Original: {secret['original']}")
                logger.info(f"Encrypted: REDACTED<${secret['encrypted']}>")

            print(f"\nProtected text:\n{protected_string}")
            return "".join(protected_text)

    async def process(
        self, request: ChatCompletionRequest, context: PipelineContext
    ) -> PipelineResult:
        """
        Process the request to find and protect secrets.

        Args:
            request: The chat completion request
            context: The pipeline context

        Returns:
            PipelineResult containing the processed request
        """
        secrets_manager = context.sensitive.manager
        if not secrets_manager or not isinstance(secrets_manager, SecretsManager):
            # Should this be an error?
            raise ValueError("Secrets manager not found in context")
        session_id = context.sensitive.session_id
        if not session_id:
            raise ValueError("Session ID not found in context")

        last_user_message = self.get_last_user_message(request)
        extracted_string = None
        extracted_index = None
        if last_user_message:
            extracted_string = last_user_message[0]
            extracted_index = last_user_message[1]

        if not extracted_string:
            return PipelineResult(request=request)

        # Protect the text
        protected_string = self._redeact_text(extracted_string, secrets_manager, session_id)

        # Update the user message
        new_request = request.copy()
        new_request["messages"][extracted_index]["content"] = protected_string
        return PipelineResult(request=new_request)
