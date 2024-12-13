import datetime
import json
from unittest.mock import AsyncMock, patch

import pytest

from codegate.dashboard.post_processing import (
    _is_system_prompt,
    parse_get_prompt_with_output,
    parse_output,
    parse_request,
)
from codegate.dashboard.request_models import (
    ChatMessage,
    Conversation,
    PartialConversation,
    QuestionAnswer,
)
from codegate.db.queries import GetPromptWithOutputsRow


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message, expected_bool",
    [
        ("Hello, how can I help you?", False),
        (
            "Given the following... please reply with a short summary that is 4-12 words in length",
            True,
        ),
    ],
)
async def test_is_system_prompt(message, expected_bool):
    result = await _is_system_prompt(message)
    assert result == expected_bool


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_dict, expected_str",
    [
        (
            {"messages": [{"role": "user", "content": "Hello, how can I help you?"}]},
            "Hello, how can I help you?",
        ),
        (
            {
                "messages": [  # Request with system prompt
                    {
                        "role": "user",
                        "content": "Given the following... please reply with a short summary",
                    }
                ]
            },
            None,
        ),
        (
            {
                "messages": [  # Request with multiple messages
                    {"role": "user", "content": "Hello, how can I help you?"},
                    {"role": "user", "content": "Hello, latest"},
                ]
            },
            "Hello, latest",
        ),
        (
            {
                "messages": [  # Request with content list
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": "Hello, how can I help you?"}],
                    },
                ]
            },
            "Hello, how can I help you?",
        ),
        ({"prompt": "Hello, how can I help you?"}, "Hello, how can I help you?"),
    ],
)
async def test_parse_request(request_dict, expected_str):
    request_str = json.dumps(request_dict)
    result = await parse_request(request_str)
    assert result == expected_str


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output_dict, expected_str, expected_chat_id",
    [
        (
            [  # Stream output with multiple chunks
                {
                    "id": "chatcmpl-AaQw9O1O2u360mhba5UbMoPwFgqEl",
                    "created": 1733246717,
                    "model": "gpt-4o-mini",
                    "object": "chat.completion.chunk",
                    "system_fingerprint": "fp_0705bf87c0",
                    "choices": [{"index": 0, "delta": {"content": "Hello", "role": "assistant"}}],
                },
                {
                    "id": "chatcmpl-AaQw9O1O2u360mhba5UbMoPwFgqEl",
                    "created": 1733246717,
                    "model": "gpt-4o-mini",
                    "object": "chat.completion.chunk",
                    "system_fingerprint": "fp_0705bf87c0",
                    "choices": [{"index": 0, "delta": {"content": " world"}}],
                },
                {
                    "id": "chatcmpl-AaQw9O1O2u360mhba5UbMoPwFgqEl",
                    "created": 1733246717,
                    "model": "gpt-4o-mini",
                    "object": "chat.completion.chunk",
                    "system_fingerprint": "fp_0705bf87c0",
                    "choices": [{"finish_reason": "stop", "index": 0, "delta": {}}],
                },
            ],
            "Hello world",
            "chatcmpl-AaQw9O1O2u360mhba5UbMoPwFgqEl",
        ),
        (
            {
                "id": "chatcmpl-AaQw9O1O2u360mhba5UbMoPwFgqEa",
                "created": 1733246717,
                "model": "gpt-4o-mini",
                "object": "chat.completion.chunk",
                "system_fingerprint": "fp_0705bf87c0",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "index": 0,
                        "message": {"content": "User seeks", "role": "assistant"},
                    }
                ],
            },
            "User seeks",
            "chatcmpl-AaQw9O1O2u360mhba5UbMoPwFgqEa",
        ),
    ],
)
async def test_parse_output(output_dict, expected_str, expected_chat_id):
    request_str = json.dumps(output_dict)
    output_message, chat_id = await parse_output(request_str)
    assert output_message == expected_str
    assert chat_id == expected_chat_id


timestamp_now = datetime.datetime.now(datetime.timezone.utc)


@pytest.mark.asyncio
@pytest.mark.parametrize("request_msg_str", ["Hello", None])
@pytest.mark.parametrize("output_msg_str", ["Hello, how can I help you?", None])
@pytest.mark.parametrize("chat_id", ["chatcmpl-AaQw9O1O2u360mhba5UbMoPwFgqEl", None])
@pytest.mark.parametrize(
    "row",
    [
        GetPromptWithOutputsRow(
            id="1",
            timestamp=timestamp_now,
            provider="provider",
            request="foo",
            type="chat",
            output_id="2",
            output="bar",
            output_timestamp=timestamp_now,
        )
    ],
)
async def test_parse_get_prompt_with_output(request_msg_str, output_msg_str, chat_id, row):
    with patch(
        "codegate.dashboard.post_processing.parse_request", new_callable=AsyncMock
    ) as mock_parse_request:
        with patch(
            "codegate.dashboard.post_processing.parse_output", new_callable=AsyncMock
        ) as mock_parse_output:
            # Set return values for the mocks
            mock_parse_request.return_value = request_msg_str
            mock_parse_output.return_value = (output_msg_str, chat_id)
            result = await parse_get_prompt_with_output(row)

            mock_parse_request.assert_called_once()
            mock_parse_output.assert_called_once()

            if any([request_msg_str is None, output_msg_str is None, chat_id is None]):
                assert result is None
            else:
                assert result.question_answer.question.message == request_msg_str
                assert result.question_answer.answer.message == output_msg_str
                assert result.chat_id == chat_id
                assert result.provider == "provider"
                assert result.type == "chat"
                assert result.request_timestamp == timestamp_now


question_answer = QuestionAnswer(
    question=ChatMessage(
        message="Hello, how can I help you?",
        timestamp=timestamp_now,
        message_id="1",
    ),
    answer=ChatMessage(
        message="Hello, how can I help you?",
        timestamp=timestamp_now,
        message_id="2",
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "partial_conversations, expected_conversations",
    [
        ([None], []),  # Test empty list
        (
            [
                None,
                PartialConversation(  # Test partial conversation with None
                    question_answer=question_answer,
                    provider="provider",
                    type="chat",
                    chat_id="chat_id",
                    request_timestamp=timestamp_now,
                ),
            ],
            [
                Conversation(
                    question_answers=[question_answer],
                    provider="provider",
                    type="chat",
                    chat_id="chat_id",
                    conversation_timestamp=timestamp_now,
                )
            ],
        ),
    ],
)
async def match_conversations(partial_conversations, expected_conversations):
    result_conversations = await match_conversations(partial_conversations)
    assert result_conversations == expected_conversations
