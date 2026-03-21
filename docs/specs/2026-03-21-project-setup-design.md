# Loom: Project Setup & Architecture Design

**Date**: 2026-03-21
**Status**: Design
**Companion to**: [Loom Design Spec](2026-03-21-loom-design.md), [Implementation Milestones](implementation-milestones.md)

---

## 1. Summary

This document captures the technology choices, project structure, and architectural patterns for the Loom codebase. It covers everything needed to go from an empty repo to a working M1 implementation.

---

## 2. Technology Choices

### Language & Runtime

**Python 3.12 + uv**

The MCP Python SDK is the reference implementation. The LLM and embedding ecosystem (pydantic-ai, Anthropic SDK, OpenAI SDK) is Python-native. `uv` provides fast, reproducible package management with lockfiles.

Latency note: Loom is designed to be fast middleware called frequently by agents. The resolution hot path (`resolve`) targets sub-100ms with cached embeddings. Python is not the bottleneck — the embedding API call dominates. The architecture keeps the resolution path thin and stateless so it can be extracted into a faster service (Rust/Go) if concurrency demands outgrow Python's async model at scale.

### Framework

**FastAPI** — async, Pydantic-native, auto-generated OpenAPI docs. Thin HTTP layer over service classes.

### Database

**PostgreSQL 17 + pgvector** — relational and vector search in one store. No separate vector DB.

**asyncpg** as the driver (fastest async Postgres driver for Python). **SQLAlchemy Core** (no ORM) for query composition and Alembic migration support. Repositories translate between DB rows and Pydantic domain models.

Why no ORM: Loom's data access is CRUD + vector search + dynamic filtering. No deep relationship graphs, no lazy loading, no unit-of-work. SA Core gives typed query building without ORM overhead on the hot path.

### LLM & Embeddings

**pydantic-ai** for both LLM and embedding abstraction.

- **Embeddings**: `pydantic_ai.Embedder` with `OpenAIEmbeddingModel`. Configured for `text-embedding-3-small` (1536 dimensions) via OpenAI API. Provider-swappable via config.
- **LLM** (eval engine): pydantic-ai `Agent` or model, configured for `google/gemini-3-flash` via OpenRouter (OpenAI-compatible endpoint). Provider-swappable via config.

Both are abstracted behind thin factory functions in `providers/`. Switching provider means changing `loom.yaml`, not service code.

### MCP

**Python MCP SDK** (`mcp>=1.0`). Dual transport: stdio (default, for local agents) and SSE (for remote/shared access).

### Configuration

**pydantic-settings** loading from `loom.yaml` with env var overrides (`LOOM_` prefix). Secrets are never in YAML — only `${ENV_VAR}` references.

### Dev Database

**Docker Compose** with `pgvector/pgvector:pg17` image. One command (`docker compose up -d`) for local Postgres. The application runs directly via `uv run`, not in a container.

### Dev Tooling

- **ruff** — linting + formatting (replaces black, isort, flake8)
- **mypy** — strict type checking
- **pre-commit** — runs ruff + mypy before commit
- **pytest + pytest-asyncio** — async test support with test DB fixtures

---

## 3. Project Structure

```
loom/
├── pyproject.toml
├── loom.yaml                         # Default config (dev settings)
├── docker-compose.yml                # PostgreSQL + pgvector
├── alembic.ini
├── alembic/
│   └── versions/
│
├── src/
│   └── loom/
│       ├── __init__.py
│       ├── settings.py               # LoomSettings (pydantic-settings)
│       │
│       ├── models/                   # Pydantic domain models
│       │   ├── skill.py              # Skill, SkillVersion, SkillCreate
│       │   ├── category.py           # Category, CategoryCreate
│       │   ├── resolution.py         # ResolvedSkill, Alternative, SelectionRationale
│       │   ├── user.py               # User (minimal for M1)
│       │   └── common.py             # Shared enums, DependencyDeclaration, PrivacyImpact
│       │
│       ├── db/                       # Database layer
│       │   ├── engine.py             # asyncpg pool creation
│       │   ├── tables.py             # SQLAlchemy Core table definitions
│       │   └── repositories/
│       │       ├── skill_repo.py     # Skill data access
│       │       └── category_repo.py  # Category data access
│       │
│       ├── services/                 # Business logic
│       │   ├── registry.py           # RegistryService — skill CRUD, versioning, validation
│       │   ├── discovery.py          # DiscoveryService — search, ranking, resolution
│       │   └── eval.py               # EvalService — structural validation only in M1
│       │
│       ├── providers/                # External dependency factories
│       │   ├── embeddings.py         # Config → pydantic_ai.Embedder
│       │   └── llm.py               # Config → pydantic_ai model/agent
│       │
│       ├── api/                      # FastAPI HTTP layer
│       │   ├── app.py                # App factory, lifespan (pool, providers)
│       │   ├── deps.py               # Dependency injection (get_db, get_services)
│       │   ├── middleware.py          # API key auth, error handling
│       │   └── routes/
│       │       ├── skills.py
│       │       ├── categories.py
│       │       └── health.py
│       │
│       └── mcp/                      # MCP server layer
│           ├── server.py             # MCP server setup (stdio + SSE)
│           └── tools.py              # resolve, search, get_skill, list_categories
│
├── tests/
│   ├── conftest.py                   # Fixtures: test DB, mock providers
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_registry_service.py
│   │   └── test_discovery_service.py
│   ├── integration/
│   │   ├── test_api_skills.py
│   │   └── test_mcp_tools.py
│   └── fixtures/
│       └── skills/                   # Sample skill YAML files for tests
│
├── seeds/                            # Seed skill content (15-20 skills per M1)
│   ├── development/
│   │   └── git/
│   ├── documentation/
│   └── code-review/
│
└── docs/
    └── specs/
```

### Growth by Milestone

The structure grows as milestones land. Only M1 modules are built initially:

| Module | M1 | M2 | M3 | M4 |
|--------|:--:|:--:|:--:|:--:|
| `models/skill.py` | ✓ | | | |
| `models/category.py` | ✓ | | | |
| `models/resolution.py` | ✓ | | | |
| `models/user.py` | ✓ | | | |
| `models/common.py` | ✓ | | | |
| `models/eval.py` | | ✓ | | |
| `models/capability.py` | | | ✓ | |
| `models/usage.py` | | | | ✓ |
| `services/registry.py` | ✓ | | | |
| `services/discovery.py` | ✓ | | | |
| `services/eval.py` | stub | ✓ | | |
| `services/contribution.py` | | ✓ | | |
| `services/capability.py` | | | ✓ | |
| `db/repositories/skill_repo.py` | ✓ | | | |
| `db/repositories/category_repo.py` | ✓ | | | |
| `db/repositories/eval_repo.py` | | ✓ | | |
| `db/repositories/capability_repo.py` | | | ✓ | |

---

## 4. Architecture Pattern

### Service Layer with Dependency Injection

Services are plain classes that receive dependencies via constructor. FastAPI's `Depends()` wires them for API routes. MCP tools instantiate the same services at startup.

```
  ┌──────────┐     ┌──────────┐
  │ FastAPI   │     │ MCP      │
  │ Routes    │     │ Tools    │
  └─────┬────┘     └─────┬────┘
        │                 │
        │  (thin layers — validate input, call service, format output)
        │                 │
        ▼                 ▼
  ┌──────────────────────────┐
  │       Services           │
  │  Registry  Discovery     │
  │  Eval                    │
  └────────────┬─────────────┘
               │
     ┌─────────┼──────────┐
     │         │          │
     ▼         ▼          ▼
  ┌──────┐ ┌────────┐ ┌──────────┐
  │Repos │ │Embedder│ │LLM       │
  │(DB)  │ │        │ │Provider  │
  └──────┘ └────────┘ └──────────┘
```

**Key rules:**
- API routes and MCP tools contain no business logic
- Services depend on repositories and providers, never on FastAPI or MCP
- Repositories return Pydantic domain models, not raw rows
- Providers are instantiated from config via factory functions

### MCP ↔ FastAPI Relationship

The MCP server and FastAPI app are **separate entry points** sharing the same services:

- `uv run python -m loom.api` — starts the FastAPI HTTP server
- `uv run python -m loom.mcp.server` — starts the MCP server

Both instantiate services from the same config and connect to the same database. They can run simultaneously or independently.

---

## 5. The `resolve` Hot Path

Target: **sub-100ms with cached embeddings, ~200-250ms cold.**

```
1. Parse & validate ResolutionContext          < 1ms
2. Generate query embedding                    ~200ms (API) or < 1ms (cache)
3. pgvector cosine similarity search           ~5-20ms
4. Constraint filtering (trust, cost, deps)    < 1ms
5. Rank, select best + alternatives            < 1ms
6. Generate selection rationale                < 1ms
7. Serialize response                          < 1ms
```

### Constraint-Aware Ranking

Candidates from vector search are re-scored:

- **Hard filters** eliminate: `trust_floor` not met → rejected with reason
- **Soft scoring** re-ranks: dependency satisfaction boosts score, cost budget excess penalises
- **Alternatives**: top 3 after best match, with tradeoff descriptions
- **Rejected candidates**: near-matches that failed hard filters, with explanations

Selection rationale is deterministic string formatting in M1, not LLM-generated.

### Embedding Cache

- **Skill embeddings**: computed at ingest, stored in pgvector. Never recomputed unless content changes.
- **Query embeddings**: in-memory LRU cache keyed on query text. Handles repeated/similar queries without API calls.

---

## 6. Database Schema (M1)

### Tables

**users** — minimal for M1 (author tracking + API key auth)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| handle | TEXT UNIQUE | |
| email | TEXT UNIQUE | |
| api_key | TEXT UNIQUE | hashed |
| role | TEXT | contributor / steward / maintainer |
| signing_public_key | TEXT | nullable in M1 (signing is M2) |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**categories** — hierarchical via parent_id

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| slug | TEXT UNIQUE | e.g. "development/git" |
| name | TEXT | |
| description | TEXT | |
| parent_id | UUID FK → categories | null for root |
| created_at | TIMESTAMPTZ | |

**skills** — current/latest version

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| slug | TEXT UNIQUE | |
| name | TEXT | |
| description | TEXT | |
| content | TEXT | full markdown body |
| category_id | UUID FK → categories | |
| tags | TEXT[] | |
| scope | TEXT | community / corporate |
| version | TEXT | semver |
| author_id | UUID FK → users | |
| signature | TEXT | nullable in M1 |
| trust_tier | TEXT | experimental / community / verified |
| cost_profile | TEXT | free / low / moderate / high |
| cost_drivers | TEXT[] | |
| estimated_duration | TEXT | fast / moderate / slow |
| dependencies | JSONB | structured declarations |
| eval_spec | JSONB | scenarios + quality dimensions |
| extends | TEXT | URI reference |
| embedding | vector(1536) | pgvector |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**skill_versions** — full history

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| skill_id | UUID FK → skills | |
| version | TEXT | UNIQUE with skill_id |
| content | TEXT | |
| dependencies | JSONB | |
| eval_spec | JSONB | |
| cost_profile | TEXT | |
| cost_drivers | TEXT[] | |
| estimated_duration | TEXT | |
| extends | TEXT | |
| signature | TEXT | |
| author_id | UUID FK → users | |
| changelog | TEXT | |
| created_at | TIMESTAMPTZ | |

### Design Decisions

- **TEXT instead of Postgres ENUM**: Postgres enums are painful to migrate. Valid values are enforced by Pydantic models at the application layer.
- **category_id as FK**: Categories have their own CRUD and hierarchy. Normalised, not denormalised strings.
- **ivfflat vector index**: Simpler and sufficient at M1 scale. Switch to hnsw if recall needs improve at thousands of skills.
- **No query text logging**: Resolution queries are not stored. Privacy by design for M1 — only skill IDs and outcomes are recorded.

### Migrations

Alembic with async support. First migration creates all M1 tables + `CREATE EXTENSION IF NOT EXISTS vector`. Subsequent milestones add tables via new migrations.

---

## 7. Configuration

### loom.yaml

```yaml
database:
  url: "postgresql+asyncpg://loom:loom@localhost:5432/loom"

embedding:
  provider: "openai"
  model: "text-embedding-3-small"
  dimensions: 1536
  api_key: ${OPENAI_API_KEY}

llm:
  provider: "openrouter"
  model: "google/gemini-3-flash"
  base_url: "https://openrouter.ai/api/v1"
  api_key: ${OPENROUTER_API_KEY}

mcp:
  transports:
    - type: "stdio"
    - type: "sse"
      host: "127.0.0.1"
      port: 8080

api:
  host: "0.0.0.0"
  port: 8000
  api_key_header: "X-API-Key"
```

### LoomSettings

pydantic-settings class with `env_prefix="LOOM_"` and `env_nested_delimiter="__"`. Any YAML value is overridable via environment variable (e.g., `LOOM_DATABASE__URL`).

---

## 8. Dependencies

### Core

```
fastapi>=0.115
uvicorn[standard]>=0.34
asyncpg>=0.30
sqlalchemy>=2.0              # Core only — query building + Alembic
alembic>=1.14
pgvector>=0.3
mcp>=1.0
pydantic-ai-slim[openai,anthropic]>=0.0.39
pydantic>=2.10
pydantic-settings>=2.7
pyyaml>=6.0
pynacl>=1.5                  # ed25519, included early for M2
```

### Dev

```
pytest>=8.0
pytest-asyncio>=0.24
httpx>=0.27                  # FastAPI test client
ruff>=0.8
mypy>=1.13
pre-commit>=4.0
```

### What's NOT Included (and When It Arrives)

| Dependency | Milestone | Purpose |
|-----------|-----------|---------|
| redis / arq | M2 | Async eval pipeline, background workers |
| React / frontend tooling | M4 | Web UI |
| stripe | M5 | Billing integration |

---

## 9. Docker Compose (Dev)

```yaml
services:
  db:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_DB: loom
      POSTGRES_USER: loom
      POSTGRES_PASSWORD: loom
    ports:
      - "5432:5432"
    volumes:
      - loom_pgdata:/var/lib/postgresql/data

volumes:
  loom_pgdata:
```

Postgres only. No Redis, no app container. The FastAPI app and MCP server run locally via `uv run`.

---

## 10. MCP Tool Surface (M1)

| Tool | Input | Output |
|------|-------|--------|
| `resolve` | task_description, context? | ResolvedSkill (content, deps status, alternatives, rationale) |
| `get_skill` | slug, version? | Skill (full content, for pinned references and `extends`) |
| `search` | query, category?, trust_tier?, cost_budget? | list[SkillSummary] (metadata, no full content) |
| `list_categories` | — | list[Category] |

### Error Responses

Structured errors, not exceptions:

| Error | When |
|-------|------|
| `no_match` | No skills above confidence threshold |
| `trust_floor_not_met` | Matches exist but below requested trust tier |
| `deprecated` | Skill deprecated, includes successor pointer |
| `removed` | Skill removed (security/policy), returns 410 equivalent |

---

## 11. Privacy (Designed In, Built Later)

### M1: Schema Accommodations

- `privacy_impact` field in the dependency/trust_requirements JSONB schema:
  ```yaml
  trust_requirements:
    data_classification: "internal"
    network_access: true
    privacy_impact:
      external_data_sharing: true
      input_logging: "unknown"    # none | anonymised | full | unknown
      data_retention: "unknown"   # none | transient | persistent | unknown
  ```
- No resolution query text logging. Only skill IDs and outcomes.

### M4/M5: Full Privacy Features

- Tiered observability: corporate instances control their own audit/logging policy
- Corporate audit trails when org policy requires it
- Public registry privacy defaults: anonymous usage signals only
- `privacy_floor` context parameter for filtering skills by privacy impact
- Privacy-aware ranking in `resolve` and `search`

---

## 12. Open Decisions (Deferred)

These don't need answers for M1 but are noted for future milestones:

1. **Embedding model selection**: Starting with `text-embedding-3-small`. May switch to a higher-quality model (Voyage AI) or local model for latency.
2. **Web UI framework**: React SPA is specified in design doc for M4. May reconsider — server-rendered or lighter framework could suffice for a curation/admin dashboard.
3. **Redis vs alternatives**: M2 needs a task queue for async eval. Redis + arq is the assumed default but not committed.
4. **Vector index type**: ivfflat for M1. Evaluate hnsw if recall degrades at scale.
