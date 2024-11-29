import re

import structlog
from litellm import ChatCompletionRequest

from codegate.pipeline.base import (
    PipelineContext,
    PipelineResult,
    PipelineStep,
)
from codegate.pipeline.secrets.gatecrypto import CodeGateCrypto
from codegate.pipeline.secrets.signatures import CodegateSignatures

logger = structlog.get_logger("codegate")


class CodegateSecrets(PipelineStep):
    """Pipeline step that handles secret information requests."""

    def __init__(self):
        """Initialize the CodegateSecrets pipeline step."""
        super().__init__()
        self.crypto = CodeGateCrypto()
        self._session_store = {}
        self._encrypted_to_session = {}  # Reverse lookup index

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

    def _redeact_text(self, text: str) -> str:
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
            # Generate session key and encrypt the value
            session_id = self.crypto.generate_session_key(None).hex()
            encrypted_value = self.crypto.encrypt_token(match.value, session_id)

            print("Original value: ", match.value)
            print("Encrypted value: ", encrypted_value)
            print("Service: ", match.service)
            print("Type: ", match.type)

            # Store the mapping
            self._session_store[session_id] = {
                "original": match.value,
                "encrypted": encrypted_value,
                "service": match.service,
                "type": match.type,
            }
            # Store reverse lookup
            self._encrypted_to_session[encrypted_value] = session_id

            # Print the session store
            logger.info(f"Session store: {self._session_store}")

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

        (f"\nProtected text:\n{protected_string}")
        return protected_string

    def _get_original_value(self, encrypted_value: str) -> str:
        """
        Get the original value for an encrypted value from the session store.

        Args:
            encrypted_value: The encrypted value to look up

        Returns:
            Original value if found, or the encrypted value if not found
        """
        try:
            # Use reverse lookup index to get session_id
            session_id = self._encrypted_to_session.get(encrypted_value)
            if session_id:
                return self._session_store[session_id]["original"]
        except Exception as e:
            logger.error(f"Error looking up original value: {e}")
        return encrypted_value

    def get_by_session_id(self, session_id: str) -> dict | None:
        """
        Get stored data directly by session ID.

        Args:
            session_id: The session ID to look up

        Returns:
            Dict containing the stored data if found, None otherwise
        """
        try:
            return self._session_store.get(session_id)
        except Exception as e:
            logger.error(f"Error looking up by session ID: {e}")
            return None

    def _cleanup_session_store(self):
        """
        Securely wipe sensitive data from session stores.
        """
        try:
            # Convert and wipe original values
            for session_data in self._session_store.values():
                if "original" in session_data:
                    original_bytes = bytearray(session_data["original"].encode())
                    self.crypto.wipe_bytearray(original_bytes)

            # Clear the dictionaries
            self._session_store.clear()
            self._encrypted_to_session.clear()

            logger.info("Session stores securely wiped")
        except Exception as e:
            logger.error(f"Error during secure cleanup: {e}")

    def _unredact_text(self, protected_text: str) -> str:
        """
        Decrypt and restore the original text from protected text.

        Args:
            protected_text: The protected text containing encrypted values

        Returns:
            Original text with decrypted values
        """
        # Find all REDACTED markers
        pattern = r"REDACTED<\$([^>]+)>"

        # Start from the beginning of the text
        result = []
        last_end = 0

        # Find each REDACTED section and replace with original value
        for match in re.finditer(pattern, protected_text):
            # Add text before this match
            result.append(protected_text[last_end : match.start()])

            # Get and add the original value
            encrypted_value = match.group(1)
            original_value = self._get_original_value(encrypted_value)
            result.append(original_value)

            last_end = match.end()

        # Add any remaining text
        result.append(protected_text[last_end:])

        # Join all parts together
        unprotected_text = "".join(result)
        logger.info(f"\nUnprotected text:\n{unprotected_text}")
        return unprotected_text

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
        last_user_message = self.get_last_user_message(request)
        extracted_string = last_user_message[0] if last_user_message else None
        print(f"Original text:\n{extracted_string}")

        if not extracted_string:
            return PipelineResult(request=request)

        try:
            # Protect the text
            protected_string = self._redeact_text(extracted_string)
            print(f"\nProtected text:\n{protected_string}")

            # LLM
            unprotected_string = self._unredact_text(protected_string)
            print(f"\nUnprotected text:\n{unprotected_string}")

            # Update the user message with protected text
            if isinstance(request["messages"], list):
                for msg in request["messages"]:
                    if msg.get("role") == "user" and msg.get("content") == extracted_string:
                        msg["content"] = protected_string

            return PipelineResult(request=request)
        except Exception as e:
            logger.error(f"CodegateSecrets operation failed: {e}")

        finally:
            # Clean up sensitive data
            self._cleanup_session_store()
