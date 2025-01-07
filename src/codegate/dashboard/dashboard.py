import asyncio
import json
from typing import AsyncGenerator, List

import structlog
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import StreamingResponse

from codegate.dashboard.post_processing import (
    parse_get_alert_conversation,
    parse_messages_in_conversations,
)
from codegate.dashboard.request_models import AlertConversation, Conversation
from codegate.db.connection import DbReader, alert_queue

logger = structlog.get_logger("codegate")

dashboard_router = APIRouter(tags=["Dashboard"])
db_reader = None


def get_db_reader():
    global db_reader
    if db_reader is None:
        db_reader = DbReader()
    return db_reader


@dashboard_router.get("/dashboard/messages")
def get_messages(db_reader: DbReader = Depends(get_db_reader)) -> List[Conversation]:
    """
    Get all the messages from the database and return them as a list of conversations.
    """
    prompts_outputs = asyncio.run(db_reader.get_prompts_with_output())

    return asyncio.run(parse_messages_in_conversations(prompts_outputs))


@dashboard_router.get("/dashboard/alerts")
def get_alerts(db_reader: DbReader = Depends(get_db_reader)) -> List[AlertConversation]:
    """
    Get all the messages from the database and return them as a list of conversations.
    """
    alerts_prompt_output = asyncio.run(db_reader.get_alerts_with_prompt_and_output())
    return asyncio.run(parse_get_alert_conversation(alerts_prompt_output))


async def generate_sse_events() -> AsyncGenerator[str, None]:
    """
    SSE generator from queue
    """
    while True:
        message = await alert_queue.get()
        yield f"data: {message}\n\n"


@dashboard_router.get("/dashboard/alerts_notification")
async def stream_sse():
    """
    Send alerts event
    """
    return StreamingResponse(generate_sse_events(), media_type="text/event-stream")


def generate_openapi():
    # Create a temporary FastAPI app instance
    app = FastAPI()

    # Include your defined router
    app.include_router(dashboard_router)

    # Generate OpenAPI JSON
    openapi_schema = app.openapi()

    # Convert the schema to JSON string for easier handling or storage
    openapi_json = json.dumps(openapi_schema, indent=2)
    print(openapi_json)
