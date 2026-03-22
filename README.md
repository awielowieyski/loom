# Loom

**Loom is a capability resolution service for agents.** It helps agents choose the right skill for a task, given the tools, policies, trust requirements, and budget constraints of their environment.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for package management
- Docker (for PostgreSQL + pgvector)

## Setup

```bash
# Install dependencies
uv sync --all-extras

# Start PostgreSQL (pgvector)
docker compose up -d

# Run database migrations
uv run alembic upgrade head

# (Optional) Load seed skills — requires OPENAI_API_KEY for embeddings
OPENAI_API_KEY=your-key uv run python scripts/seed.py

# Or load without embeddings (skills created but vector search won't work)
uv run python scripts/seed.py
```

## Running

### API Server
```bash
uv run python -m loom.api
# Swagger docs at http://localhost:8000/docs
```

### MCP Server (for agent connections)
```bash
# stdio transport (default)
uv run python -m loom.mcp

# Or directly
uv run python -m loom.mcp.server
```

### Connecting from Claude Code

Add to your MCP config:
```json
{
  "mcpServers": {
    "loom": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/loom", "python", "-m", "loom.mcp"]
    }
  }
}
```

## Development

```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check src/ tests/

# Run type checking
uv run mypy src/

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

## Architecture

Loom uses a service layer architecture:

- **API layer** (`src/loom/api/`) — FastAPI routes, thin wrappers over services
- **MCP layer** (`src/loom/mcp/`) — MCP server tools, same services
- **Services** (`src/loom/services/`) — Business logic (Registry, Discovery, Eval)
- **Repositories** (`src/loom/db/repositories/`) — Data access via asyncpg
- **Providers** (`src/loom/providers/`) — Embedding and LLM abstraction via pydantic-ai
- **Models** (`src/loom/models/`) — Pydantic domain models

## MCP Tools

| Tool | Description |
|------|-------------|
| `resolve` | Find the best skill for a task, given runtime constraints |
| `get_skill` | Fetch a specific skill by slug (with optional version) |
| `search` | Browse skills by query with filters |
| `list_categories` | List the category taxonomy |

## Configuration

Settings are loaded from `loom.yaml` with environment variable overrides (`LOOM_` prefix):

```bash
# Override database URL
LOOM_DATABASE__URL="postgresql+asyncpg://user:pass@host:5432/loom"

# Override API port
LOOM_API__PORT=9000
```

## License

Apache 2.0
