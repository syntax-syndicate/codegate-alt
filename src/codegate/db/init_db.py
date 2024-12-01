import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def init_db():
    """Initialize the database with the schema."""
    # Get the absolute path to the schema file
    current_dir = Path(__file__).parent
    schema_path = current_dir.parent.parent.parent / 'sql' / 'schema' / 'schema.sql'

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")

    with open(schema_path, 'r') as f:
        schema = f.read()

    db_path = Path('codegate.db').absolute()
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=True,  # We should toggle this to true when we do release codegate
        isolation_level="AUTOCOMMIT",  # Required for SQLite
    )

    try:
        # Execute the schema
        async with engine.begin() as conn:
            # Split the schema into individual statements and execute each one
            statements = [stmt.strip() for stmt in schema.split(';') if stmt.strip()]
            for statement in statements:
                # Use SQLAlchemy text() to create executable SQL statements
                await conn.execute(text(statement))
    finally:
        await engine.dispose()

def init_db_sync():
    """Synchronous wrapper for init_db."""
    asyncio.run(init_db())

if __name__ == '__main__':
    init_db_sync()
