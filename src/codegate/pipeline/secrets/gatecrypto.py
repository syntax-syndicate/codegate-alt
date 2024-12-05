import os
import time
from base64 import b64decode, b64encode

import structlog
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = structlog.get_logger("codegate")


class CodeGateCrypto:
    """
    Manage session keys and provide encryption / decryption of tokens with replay protection.
    Attributes:
        session_keys (dict): A dictionary to store session keys with their associated timestamps.
        SESSION_KEY_LIFETIME (int): The lifetime of a session key in seconds.
        NONCE_SIZE (int): The size of the nonce used in AES GCM mode.
    Methods:
        generate_session_key(session_id):
            Generates a session key with an associated timestamp.
        get_session_key(session_id):
            Retrieves a session key if it is still valid.
        cleanup_expired_keys():
            Removes expired session keys from memory.
        encrypt_token(token, session_id):
            Encrypts a token with a session key and adds a timestamp for replay protection.
        decrypt_token(encrypted_token, session_id):
            Decrypts a token and validates its timestamp to prevent replay attacks.
        wipe_bytearray(data):
            Securely wipes a bytearray in-place.
    """

    def __init__(self):
        self.session_keys = {}
        self.SESSION_KEY_LIFETIME = 600  # 10 minutes
        self.NONCE_SIZE = 12  # AES GCM recommended nonce size

    def generate_session_key(self, session_id):
        """Generates a session key with an associated timestamp."""
        key = os.urandom(32)  # Generate a 256-bit key
        self.session_keys[session_id] = (key, time.time())
        return key

    def get_session_key(self, session_id):
        """Retrieves a session key if it is still valid."""
        key_data = self.session_keys.get(session_id)
        if key_data:
            key, timestamp = key_data
            if time.time() - timestamp < self.SESSION_KEY_LIFETIME:
                return key
            else:
                # Key has expired
                del self.session_keys[session_id]
        return None

    def cleanup_expired_keys(self):
        """Removes expired session keys from memory."""
        now = time.time()
        expired_keys = [
            session_id
            for session_id, (key, timestamp) in self.session_keys.items()
            if now - timestamp >= self.SESSION_KEY_LIFETIME
        ]
        for session_id in expired_keys:
            del self.session_keys[session_id]

    def encrypt_token(self, token, session_id):
        """Encrypts a token with a session key and adds a timestamp for replay protection."""
        key = self.generate_session_key(session_id)
        nonce = os.urandom(self.NONCE_SIZE)
        timestamp = int(time.time())
        data = f"{token}:{timestamp}".encode()  # Append timestamp to token

        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)  # None for no associated data

        # Combine nonce and ciphertext (which includes the authentication tag)
        encrypted_token = b64encode(nonce + ciphertext).decode()
        return encrypted_token

    def decrypt_token(self, encrypted_token, session_id):
        """Decrypts a token and validates its timestamp to prevent replay attacks."""
        key = self.get_session_key(session_id)
        if not key:
            raise ValueError("Session key expired or invalid.")

        encrypted_data = b64decode(encrypted_token)
        nonce = encrypted_data[: self.NONCE_SIZE]
        ciphertext = encrypted_data[self.NONCE_SIZE :]  # Includes authentication tag

        aesgcm = AESGCM(key)
        try:
            decrypted_data = aesgcm.decrypt(
                nonce, ciphertext, None
            ).decode()  # None for no associated data
        except Exception as e:
            raise ValueError("Decryption failed: Invalid token or tampering detected.") from e

        token, timestamp = decrypted_data.rsplit(":", 1)
        if time.time() - int(timestamp) > self.SESSION_KEY_LIFETIME:
            raise ValueError("Token has expired.")

        return token

    def wipe_bytearray(self, data):
        """Securely wipes a bytearray in-place."""
        if not isinstance(data, bytearray):
            raise ValueError("Only bytearray objects can be securely wiped.")
        for i in range(len(data)):
            data[i] = 0  # Overwrite each byte with 0
        logger.info("Sensitive data securely wiped from memory.")
