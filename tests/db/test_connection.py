import hashlib
from unittest.mock import patch

import pytest

from codegate.db.connection import DbRecorder


@patch("codegate.db.connection.DbRecorder.__init__", return_value=None)
def mock_db_recorder(mocked_init) -> DbRecorder:
    db_recorder = DbRecorder()
    return db_recorder


fim_message = """
# Path: folder/testing_file.py
# another_folder/another_file.py

This is a test message
"""


@pytest.mark.parametrize(
    "message, provider, expected_message_to_hash",
    [
        ("This is a test message", "test_provider", "This is a test message-test_provider"),
        (fim_message, "copilot", "folder/testing_file.py-copilot"),
        (fim_message, "other", "another_folder/another_file.py-other"),
    ],
)
def test_create_hash_key(message, provider, expected_message_to_hash):
    mocked_db_recorder = mock_db_recorder()
    expected_hash = hashlib.sha256(expected_message_to_hash.encode("utf-8")).hexdigest()

    result_hash = mocked_db_recorder._create_hash_key(message, provider)
    assert result_hash == expected_hash
