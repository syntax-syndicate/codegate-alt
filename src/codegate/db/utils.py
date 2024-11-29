import uuid
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from codegate.db.models import Prompt
from codegate.db.queries import AsyncQuerier


async def create_prompt_record(
    conn: AsyncConnection,
    data: Dict,
    provider: str,
    prompt_type: str,
) -> Optional[Prompt]:
    """Create a prompt record in the database."""
    AsyncQuerier(conn)

    # Extract system prompt and user prompt from the messages
    messages = data.get("messages", [])
    system_prompt = None
    user_prompt = None

    for msg in messages:
        if msg.get("role") == "system":
            system_prompt = msg.get("content")
        elif msg.get("role") == "user":
            user_prompt = msg.get("content")

    # If no user prompt found in messages, try to get from the prompt field
    # (for non-chat completions)
    if not user_prompt:
        user_prompt = data.get("prompt")

    if not user_prompt:
        return None

    # Create the prompt record
    sql = text(
        """
        INSERT INTO prompts (id, timestamp, provider, system_prompt, user_prompt, type, status)
        VALUES (:id, :timestamp, :provider, :system_prompt, :user_prompt, :type, :status)
        RETURNING *
    """
    )

    result = await conn.execute(
        sql,
        {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow(),
            "provider": provider,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "type": prompt_type,
            "status": "processing",
        },
    )

    row = result.first()
    if row is None:
        return None

    return Prompt(
        id=row.id,
        timestamp=row.timestamp,
        provider=row.provider,
        system_prompt=row.system_prompt,
        user_prompt=row.user_prompt,
        type=row.type,
        status=row.status,
    )
