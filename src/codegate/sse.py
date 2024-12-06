from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from codegate.db.connection import alert_queue

router = APIRouter(tags=["SSE"])

async def generate_sse_events() -> AsyncGenerator[str, None]:
    """
    SSE generator from queue
    """
    while True:
        message = await alert_queue.get()
        yield f"data: {message}\n\n"

@router.get("/alerts_notification")
async def stream_sse():
    """
    Send alerts event
    """
    return StreamingResponse(generate_sse_events(), media_type="text/event-stream")