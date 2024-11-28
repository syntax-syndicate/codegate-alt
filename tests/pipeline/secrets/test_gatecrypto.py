import time

import pytest

from codegate.pipeline.secrets.gatecrypto import CodeGateCrypto


@pytest.fixture
def crypto():
    return CodeGateCrypto()


def test_generate_session_key(crypto):
    session_id = "test_session"
    key = crypto.generate_session_key(session_id)

    assert len(key) == 32  # AES-256 key size
    assert session_id in crypto.session_keys
    assert isinstance(crypto.session_keys[session_id], tuple)
    assert len(crypto.session_keys[session_id]) == 2


def test_get_session_key(crypto):
    session_id = "test_session"
    original_key = crypto.generate_session_key(session_id)
    retrieved_key = crypto.get_session_key(session_id)

    assert original_key == retrieved_key


def test_get_expired_session_key(crypto):
    session_id = "test_session"
    crypto.generate_session_key(session_id)

    # Manually expire the key by modifying its timestamp
    key, _ = crypto.session_keys[session_id]
    crypto.session_keys[session_id] = (key, time.time() - (crypto.SESSION_KEY_LIFETIME + 10))

    retrieved_key = crypto.get_session_key(session_id)
    assert retrieved_key is None
    assert session_id not in crypto.session_keys


def test_cleanup_expired_keys(crypto):
    # Generate multiple session keys
    session_ids = ["session1", "session2", "session3"]
    for session_id in session_ids:
        crypto.generate_session_key(session_id)

    # Manually expire some keys
    key, _ = crypto.session_keys["session1"]
    crypto.session_keys["session1"] = (key, time.time() - (crypto.SESSION_KEY_LIFETIME + 10))
    key, _ = crypto.session_keys["session2"]
    crypto.session_keys["session2"] = (key, time.time() - (crypto.SESSION_KEY_LIFETIME + 10))

    crypto.cleanup_expired_keys()

    assert "session1" not in crypto.session_keys
    assert "session2" not in crypto.session_keys
    assert "session3" in crypto.session_keys


def test_encrypt_decrypt_token(crypto):
    session_id = "test_session"
    original_token = "sensitive_data_123"

    encrypted_token = crypto.encrypt_token(original_token, session_id)
    decrypted_token = crypto.decrypt_token(encrypted_token, session_id)

    assert decrypted_token == original_token


def test_decrypt_with_expired_session(crypto):
    session_id = "test_session"
    token = "sensitive_data_123"

    encrypted_token = crypto.encrypt_token(token, session_id)

    # Manually expire the session key
    key, _ = crypto.session_keys[session_id]
    crypto.session_keys[session_id] = (key, time.time() - (crypto.SESSION_KEY_LIFETIME + 10))

    with pytest.raises(ValueError, match="Session key expired or invalid."):
        crypto.decrypt_token(encrypted_token, session_id)


def test_decrypt_with_invalid_session(crypto):
    session_id = "test_session"
    token = "sensitive_data_123"

    encrypted_token = crypto.encrypt_token(token, session_id)

    with pytest.raises(ValueError, match="Session key expired or invalid."):
        crypto.decrypt_token(encrypted_token, "invalid_session")


def test_decrypt_with_expired_token(crypto, monkeypatch):
    session_id = "test_session"
    token = "sensitive_data_123"
    current_time = time.time()

    # Mock time.time() for token encryption
    monkeypatch.setattr(time, "time", lambda: current_time)

    # Generate token with current timestamp
    encrypted_token = crypto.encrypt_token(token, session_id)

    # Mock time.time() to return a future timestamp for decryption
    future_time = current_time + crypto.SESSION_KEY_LIFETIME + 10
    monkeypatch.setattr(time, "time", lambda: future_time)

    # Keep the original key but update its timestamp to keep it valid
    key, _ = crypto.session_keys[session_id]
    crypto.session_keys[session_id] = (key, future_time)

    with pytest.raises(ValueError, match="Token has expired."):
        crypto.decrypt_token(encrypted_token, session_id)


def test_wipe_bytearray(crypto):
    # Create a bytearray with sensitive data
    sensitive_data = bytearray(b"sensitive_information")
    original_content = sensitive_data.copy()

    # Wipe the data
    crypto.wipe_bytearray(sensitive_data)

    # Verify all bytes are zeroed
    assert all(byte == 0 for byte in sensitive_data)
    assert sensitive_data != original_content


def test_wipe_bytearray_invalid_input(crypto):
    # Try to wipe a string instead of bytearray
    with pytest.raises(ValueError, match="Only bytearray objects can be securely wiped."):
        crypto.wipe_bytearray("not a bytearray")


def test_encrypt_decrypt_with_special_characters(crypto):
    session_id = "test_session"
    special_chars_token = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    encrypted_token = crypto.encrypt_token(special_chars_token, session_id)
    decrypted_token = crypto.decrypt_token(encrypted_token, session_id)

    assert decrypted_token == special_chars_token


def test_encrypt_decrypt_multiple_tokens(crypto):
    session_id = "test_session"
    tokens = ["token1", "token2", "token3"]

    # Encrypt and immediately decrypt each token
    for token in tokens:
        encrypted = crypto.encrypt_token(token, session_id)
        decrypted = crypto.decrypt_token(encrypted, session_id)
        assert decrypted == token
