# SQLC Documentation

## Overview

This project uses [sqlc](https://sqlc.dev/) with SQLite to generate type-safe Python code from SQL. The configuration is managed through `sqlc.yaml` in the root directory.

## Setup and Configuration

The project uses the following sqlc configuration:

```yaml
version: "2"
plugins:
  - name: "python"
    wasm:
      url: "https://downloads.sqlc.dev/plugin/sqlc-gen-python_1.2.0.wasm"
      sha256: "a6c5d174c407007c3717eea36ff0882744346e6ba991f92f71d6ab2895204c0e"

sql:
  - engine: "sqlite"
    schema: "sql/schema"
    queries: "sql/queries"
    codegen:
      - plugin: "python"
        out: "src/codegate/db"
        options:
          package: "codegate.db"
          emit_sync_querier: true
          emit_async_querier: true
          query_parameter_limit: 5
```

## Directory Structure

```
sql/
├── queries/    # Contains SQL query files
│   └── queries.sql
└── schema/     # Contains database schema
    └── schema.sql
```

## Generating Code

To generate Python code from your SQL files:

1. Install sqlc (if not already installed)
   ```bash
   brew install sqlc
   ```

2. Run the following command from the project root:
   ```bash
   sqlc generate
   ```

This will generate code in `src/codegate/db/` based on the schema and queries.

## Creating New Queries

Queries are defined in `sql/queries/queries.sql`. Each query must have a name and a command type annotation. Here are the supported command types:

- `:one` - Returns a single row
- `:many` - Returns multiple rows
- `:exec` - Executes a query without returning results

### Query Example

```sql
-- name: CreatePrompt :one
INSERT INTO prompts (
    id,
    timestamp,
    provider,
    system_prompt,
    user_prompt,
    type,
    status
) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING *;

-- name: ListPrompts :many
SELECT * FROM prompts 
ORDER BY timestamp DESC 
LIMIT ? OFFSET ?;
```

### Query Naming Conventions

- Use PascalCase for query names
- Prefix with action (Create, Get, List, Update, Delete)
- Be descriptive about what the query does

## Using Generated Queries in Code

The generated code provides both synchronous and asynchronous query interfaces. Here are examples of how to use the generated queries:

### Synchronous Usage

```python
from codegate.db.queries import Queries
from sqlite3 import Connection

def create_prompt(conn: Connection, 
                 id: str,
                 timestamp: datetime,
                 provider: str,
                 system_prompt: str,
                 user_prompt: str,
                 type: str,
                 status: str):
    queries = Queries(conn)
    prompt = queries.create_prompt(
        id=id,
        timestamp=timestamp,
        provider=provider,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        type=type,
        status=status
    )
    return prompt

def list_prompts(conn: Connection, limit: int, offset: int):
    queries = Queries(conn)
    prompts = queries.list_prompts(limit=limit, offset=offset)
    return prompts
```

### Asynchronous Usage

```python
from codegate.db.queries import AsyncQuerier
import aiosqlite

async def create_prompt_async(conn: aiosqlite.Connection,
                            id: str,
                            timestamp: datetime,
                            provider: str,
                            system_prompt: str,
                            user_prompt: str,
                            type: str,
                            status: str):
    queries = AsyncQuerier(conn)
    prompt = await queries.create_prompt(
        id=id,
        timestamp=timestamp,
        provider=provider,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        type=type,
        status=status
    )
    return prompt

async def list_prompts_async(conn: aiosqlite.Connection, limit: int, offset: int):
    queries = AsyncQuerier(conn)
    prompts = await queries.list_prompts(limit=limit, offset=offset)
    return prompts
```

## Best Practices

1. **Schema Changes**
   - Always update schema.sql when making database changes
   - Run `sqlc generate` after any schema changes
   - Commit both schema changes and generated code

2. **Query Organization**
   - Keep related queries together in the queries.sql file
   - Use clear, descriptive names for queries
   - Include comments for complex queries

3. **Error Handling**
   - Always handle database errors appropriately
   - Use transactions for operations that need to be atomic
   - Validate input parameters before executing queries

4. **Performance**
   - Use appropriate indexes (defined in schema.sql)
   - Be mindful of query complexity
   - Use LIMIT and OFFSET for pagination

## Current Implementation Review and Recommendations

### Type Safety Improvements

The current implementation uses `Any` for all model fields. Consider adding type hints:

```python
@dataclasses.dataclass()
class Prompt:
    id: str  # Instead of Any
    timestamp: datetime  # Instead of Any
    provider: Optional[str]  # Instead of Optional[Any]
    system_prompt: Optional[str]
    user_prompt: str
    type: str
    status: str
```
