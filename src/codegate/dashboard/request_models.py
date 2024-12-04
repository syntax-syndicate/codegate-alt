import datetime
from typing import List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """
    Represents a chat message.
    """

    message: str
    timestamp: datetime.datetime
    message_id: str


class QuestionAnswer(BaseModel):
    """
    Represents a question and answer pair.
    """

    question: ChatMessage
    answer: ChatMessage


class PartialConversation(BaseModel):
    """
    Represents a partial conversation obtained from a DB row.
    """

    question_answer: QuestionAnswer
    provider: Optional[str]
    type: str
    chat_id: str
    request_timestamp: datetime.datetime


class Conversation(BaseModel):
    """
    Represents a conversation.
    """

    question_answers: List[QuestionAnswer]
    provider: Optional[str]
    type: str
    chat_id: str
    conversation_timestamp: datetime.datetime
