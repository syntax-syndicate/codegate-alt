import copy
from typing import Dict, List, NamedTuple

from codegate.pipeline.secrets.signatures import CodegateSignatures


class SecretPosition(NamedTuple):
    """Stores exact position and value of a secret for reliable restoration"""

    line_number: int
    start_index: int
    end_index: int
    value: str


class SecretManager:
    """Manages finding, redacting and restoring secrets in text"""

    def __init__(self, signatures_path: str = "signatures.yaml"):
        """Initialize with path to signatures file"""
        CodegateSignatures.initialize(signatures_path)
        self._secret_store: Dict[str, List[SecretPosition]] = {}

    def _generate_key(self, text: str) -> str:
        """Generate unique key for text block to store its secrets"""
        return str(hash(text))

    def find_and_redact(self, text: str) -> str:
        """Find secrets in text and replace with REDACTED while preserving structure"""
        if not text:
            return text

        # Get matches using CodegateSignatures
        matches = CodegateSignatures.find_in_string(text)
        if not matches:
            return text

        # Convert text to lines for precise replacement
        lines = text.splitlines()

        # Store original text key
        text_key = self._generate_key(text)
        self._secret_store[text_key] = []

        # Create copy of lines to modify
        modified_lines = copy.deepcopy(lines)

        # Process each match, store original value and replace with REDACTED
        for match in matches:
            # Store original value and position
            secret_pos = SecretPosition(
                line_number=match.line_number,
                start_index=match.start_index,
                end_index=match.end_index,
                value=match.value,
            )
            self._secret_store[text_key].append(secret_pos)

            # Replace in the copied lines
            line = modified_lines[match.line_number - 1]  # -1 since line numbers are 1-based
            modified_lines[match.line_number - 1] = (
                line[: match.start_index] + "REDACTED" + line[match.end_index :]
            )

        # Reconstruct text with replacements
        return "\n".join(modified_lines)

    def restore(self, redacted_text: str) -> str:
        """Restore original secrets to redacted text"""
        if not redacted_text:
            return redacted_text

        # Get stored secrets for this text
        text_key = self._generate_key(redacted_text)
        stored_secrets = self._secret_store.get(text_key)
        if not stored_secrets:
            return redacted_text

        # Convert to lines for precise restoration
        lines = redacted_text.splitlines()

        # Create copy of lines to modify
        restored_lines = copy.deepcopy(lines)

        # Restore each secret
        for secret in stored_secrets:
            line = restored_lines[secret.line_number - 1]
            restored_lines[secret.line_number - 1] = (
                line[: secret.start_index] + secret.value + line[secret.end_index :]
            )

        # Reconstruct text with restored values
        return "\n".join(restored_lines)


def main():
    # Original text with secrets
    text = """from flask import Flask, request, jsonify
import os
import hashlib

GITHUB_TOKEN = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"

app = Flask(__name__)

@app.route('/api/data', methods=['GET'])
def get_data():
    # Insecure: No input validation
    AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"

    return {"data": "This is some insecure data!"}"""

    # Create secret manager
    manager = SecretManager()

    # Find and redact secrets
    print("Original text:")
    print("-" * 80)
    print(text)
    print("\nRedacted text:")
    print("-" * 80)
    redacted = manager.find_and_redact(text)
    print(redacted)

    # Restore original secrets
    print("\nRestored text:")
    print("-" * 80)
    restored = manager.restore(redacted)
    print(restored)

    # Verify restoration matches original
    print("\nVerification:")
    print("-" * 80)
    print(f"Restoration successful: {text == restored}")


if __name__ == "__main__":
    main()
