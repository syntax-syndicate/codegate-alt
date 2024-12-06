from unittest.mock import Mock

import pytest

from codegate.pipeline.base import PipelineContext
from codegate.pipeline.systemmsg import add_or_update_system_message, get_existing_system_message


class TestAddOrUpdateSystemMessage:
    def test_init_with_system_message(self):
        """
        Test creating a system message
        """
        test_message = {"role": "system", "content": "Test system prompt"}
        context = Mock(spec=PipelineContext)
        context.add_alert = Mock()

        request = {"messages": []}
        result = add_or_update_system_message(request, test_message, context)

        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == test_message["content"]

    @pytest.mark.parametrize(
        "request_setup",
        [{"messages": [{"role": "user", "content": "Test user message"}]}, {"messages": []}, {}],
    )
    def test_system_message_insertion(self, request_setup):
        """
        Test system message insertion in various request scenarios
        """
        context = Mock(spec=PipelineContext)
        context.add_alert = Mock()

        system_message = {"role": "system", "content": "Security analysis system prompt"}

        result = add_or_update_system_message(request_setup, system_message, context)

        assert len(result["messages"]) > 0
        assert result["messages"][0]["role"] == "system"
        assert result["messages"][0]["content"] == system_message["content"]
        context.add_alert.assert_called_once()

    def test_update_existing_system_message(self):
        """
        Test updating an existing system message
        """
        existing_system_message = {"role": "system", "content": "Existing system message"}
        request = {"messages": [existing_system_message]}
        context = Mock(spec=PipelineContext)
        context.add_alert = Mock()

        new_system_message = {"role": "system", "content": "Additional system instructions"}

        result = add_or_update_system_message(request, new_system_message, context)

        assert len(result["messages"]) == 1
        expected_content = "Existing system message" + "\n\n" + "Additional system instructions"

        assert result["messages"][0]["content"] == expected_content
        context.add_alert.assert_called_once_with(
            "update-system-message", trigger_string=expected_content
        )

    @pytest.mark.parametrize(
        "edge_case",
        [
            None,  # No messages
            [],  # Empty messages list
        ],
    )
    def test_edge_cases(self, edge_case):
        """
        Test edge cases with None or empty message list
        """
        request = {"messages": edge_case} if edge_case is not None else {}
        context = Mock(spec=PipelineContext)
        context.add_alert = Mock()

        system_message = {"role": "system", "content": "Security edge case prompt"}

        result = add_or_update_system_message(request, system_message, context)

        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "system"
        assert result["messages"][0]["content"] == system_message["content"]
        context.add_alert.assert_called_once()


class TestGetExistingSystemMessage:
    def test_existing_system_message(self):
        """
        Test retrieving an existing system message
        """
        system_message = {"role": "system", "content": "Existing system message"}
        request = {"messages": [system_message, {"role": "user", "content": "User message"}]}

        result = get_existing_system_message(request)

        assert result == system_message

    def test_no_system_message(self):
        """
        Test when there is no system message in the request
        """
        request = {"messages": [{"role": "user", "content": "User message"}]}

        result = get_existing_system_message(request)

        assert result is None

    def test_empty_messages(self):
        """
        Test when the messages list is empty
        """
        request = {"messages": []}

        result = get_existing_system_message(request)

        assert result is None

    def test_no_messages_key(self):
        """
        Test when the request has no 'messages' key
        """
        request = {}

        result = get_existing_system_message(request)

        assert result is None

    def test_multiple_system_messages(self):
        """
        Test when there are multiple system messages, should return the first one
        """
        system_message1 = {"role": "system", "content": "First system message"}
        system_message2 = {"role": "system", "content": "Second system message"}
        request = {"messages": [system_message1, system_message2]}

        result = get_existing_system_message(request)

        assert result == system_message1
