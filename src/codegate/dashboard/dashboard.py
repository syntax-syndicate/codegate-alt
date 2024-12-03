import asyncio
from typing import List

import structlog
from fastapi import APIRouter

from codegate.dashboard.post_processing import match_conversations, parse_get_prompt_with_output
from codegate.dashboard.request_models import Conversation
from codegate.db.connection import DbReader

logger = structlog.get_logger("codegate")

dashboard_router = APIRouter(tags=["Dashboard"])
db_reader = DbReader()


@dashboard_router.get("/dashboard/messages")
async def get_messages() -> List[Conversation]:
    """
    Get all the messages from the database and return them as a list of conversations.
    """
    prompts_outputs = await db_reader.get_prompts_with_output()

    # Parse the prompts and outputs in parallel
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(parse_get_prompt_with_output(row)) for row in prompts_outputs]
    partial_conversations = [task.result() for task in tasks]

    conversations = await match_conversations(partial_conversations)
    return conversations
