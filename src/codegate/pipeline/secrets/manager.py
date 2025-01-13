from typing import NamedTuple, Optional

import structlog

from codegate.pipeline.secrets.gatecrypto import CodeGateCrypto

logger = structlog.get_logger("codegate")


class SecretEntry(NamedTuple):
    """Represents a stored secret"""

    original: str
    encrypted: str
    service: str
    secret_type: str


class SecretsManager:
    """Manages encryption, storage and retrieval of secrets"""

    def __init__(self):
        self.crypto = CodeGateCrypto()
        self._session_store: dict[str, dict[str, SecretEntry]] = {}
        self._encrypted_to_session: dict[str, str] = {}  # Reverse lookup index

    def store_secret(self, value: str, service: str, secret_type: str, session_id: str) -> str:
        """
        Encrypts and stores a secret value.
        Returns the encrypted value.
        """
        if not value:
            raise ValueError("Value must be provided")
        if not service:
            raise ValueError("Service must be provided")
        if not secret_type:
            raise ValueError("Secret type must be provided")
        if not session_id:
            raise ValueError("Session ID must be provided")

        encrypted_value = self.crypto.encrypt_token(value, session_id)

        # Store mappings
        session_secrets = self._session_store.get(session_id, {})
        session_secrets[encrypted_value] = SecretEntry(
            original=value,
            encrypted=encrypted_value,
            service=service,
            secret_type=secret_type,
        )
        self._session_store[session_id] = session_secrets
        self._encrypted_to_session[encrypted_value] = session_id

        logger.debug("Stored secret", service=service, type=secret_type, encrypted=encrypted_value)

        return encrypted_value

    def get_original_value(self, encrypted_value: str, session_id: str) -> Optional[str]:
        """Retrieve original value for an encrypted value"""
        try:
            stored_session_id = self._encrypted_to_session.get(encrypted_value)
            if stored_session_id == session_id:
                session_secrets = self._session_store[session_id].get(encrypted_value)
                if session_secrets:
                    return session_secrets.original
        except Exception as e:
            logger.error("Error retrieving secret", error=str(e))
        return None

    def get_by_session_id(self, session_id: str) -> Optional[SecretEntry]:
        """Get stored data by session ID"""
        return self._session_store.get(session_id)

    def cleanup(self):
        """Securely wipe sensitive data"""
        try:
            # Convert and wipe original values
            for secrets in self._session_store.values():
                for entry in secrets.values():
                    original_bytes = bytearray(entry.original.encode())
                    self.crypto.wipe_bytearray(original_bytes)

            # Clear the dictionaries
            self._session_store.clear()
            self._encrypted_to_session.clear()

            logger.info("Secrets manager data securely wiped")
        except Exception as e:
            logger.error("Error during secure cleanup", error=str(e))

    def cleanup_session(self, session_id: str):
        """
        Remove a specific session's secrets and perform secure cleanup.

        Args:
            session_id (str): The session identifier to remove
        """
        try:
            # Get the secret entry for the session
            secrets = self._session_store.get(session_id, {})

            for entry in secrets.values():
                # Securely wipe the original value
                original_bytes = bytearray(entry.original.encode())
                self.crypto.wipe_bytearray(original_bytes)

                # Remove the encrypted value from the reverse lookup index
                self._encrypted_to_session.pop(entry.encrypted, None)

                # Remove the session from the store
                self._session_store.pop(session_id, None)

                logger.debug("Session secrets securely removed", session_id=session_id)
            else:
                logger.debug("No secrets found for session", session_id=session_id)
        except Exception as e:
            logger.error("Error during session cleanup", session_id=session_id, error=str(e))
