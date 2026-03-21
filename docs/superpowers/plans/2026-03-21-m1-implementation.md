# M1: Constraint-Aware MCP Skill Resolution — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working MCP server that resolves skills by natural language description and runtime constraints, backed by a FastAPI REST API, PostgreSQL + pgvector, and pydantic-ai for embeddings.

**Architecture:** Service layer with dependency injection. FastAPI and MCP are thin entry points over shared services (RegistryService, DiscoveryService, EvalService). Repositories handle all DB access via asyncpg + SQLAlchemy Core. Providers abstract embeddings (pydantic-ai Embedder) and LLM (pydantic-ai OpenRouter). Config via pydantic-settings + YAML.

**Tech Stack:** Python 3.12, uv, FastAPI, asyncpg, SQLAlchemy Core (no ORM), Alembic, pgvector, pydantic-ai (embeddings + LLM), MCP Python SDK (FastMCP), Docker Compose (Postgres), pytest + pytest-asyncio.

**Spec references:**
- [Project Setup Design](../../specs/2026-03-21-project-setup-design.md)
- [Loom Design Spec](../../specs/2026-03-21-loom-design.md)
- [Implementation Milestones](../../specs/implementation-milestones.md)

---

## Chunk 1: Project Scaffolding & Infrastructure

### Task 1: Initialize Python Project

**Files:**
- Create: `pyproject.toml`
- Create: `src/loom/__init__.py`
- Create: `.python-version`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "loom"
version = "0.1.0"
description = "Capability resolution service for agents"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "asyncpg>=0.30",
    "sqlalchemy>=2.0",
    "alembic>=1.14",
    "pgvector>=0.3",
    "mcp>=1.0",
    "pydantic-ai-slim[openai,openrouter]>=0.0.39",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "pyyaml>=6.0",
    "pynacl>=1.5",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
    "ruff>=0.8",
    "mypy>=1.13",
    "pre-commit>=4.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/loom"]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "TCH"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
mypy_path = "src"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
```

- [ ] **Step 2: Create package init**

Create `src/loom/__init__.py`:

```python
"""Loom: Capability resolution service for agents."""
```

Create `.python-version`:

```
3.12
```

- [ ] **Step 3: Install dependencies**

Run: `uv sync --all-extras`
Expected: Lockfile created, all deps installed.

- [ ] **Step 4: Verify tooling works**

Run: `uv run ruff check src/ && uv run mypy src/`
Expected: No errors (empty package).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/loom/__init__.py .python-version
git commit -m "feat: initialize Python project with uv and dependencies"
```

---

### Task 2: Docker Compose & Configuration

**Files:**
- Create: `docker-compose.yml`
- Create: `loom.yaml`
- Create: `loom.prod.yaml` (gitignored template)
- Create: `.gitignore`
- Create: `src/loom/settings.py`

- [ ] **Step 1: Create .gitignore**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
.mypy_cache/
.pytest_cache/
.ruff_cache/
.DS_Store
loom.prod.yaml
.env
```

- [ ] **Step 2: Create docker-compose.yml**

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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U loom"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  loom_pgdata:
```

- [ ] **Step 3: Create loom.yaml**

```yaml
database:
  url: "postgresql+asyncpg://loom:loom@localhost:5432/loom"

embedding:
  provider: "openai"
  model: "text-embedding-3-small"
  dimensions: 1536

llm:
  provider: "openrouter"
  model: "google/gemini-3-flash"

mcp:
  transports:
    - type: "stdio"
    - type: "sse"
      host: "127.0.0.1"
      port: 8080

api:
  host: "0.0.0.0"
  port: 8000
```

- [ ] **Step 4: Write the failing test for settings**

Create `tests/__init__.py` (empty).
Create `tests/unit/__init__.py` (empty).
Create `tests/unit/test_settings.py`:

```python
import os

from loom.settings import LoomSettings


def test_settings_loads_defaults():
    """Settings should load from loom.yaml with sensible defaults."""
    settings = LoomSettings()
    assert settings.database.url == "postgresql+asyncpg://loom:loom@localhost:5432/loom"
    assert settings.embedding.model == "text-embedding-3-small"
    assert settings.embedding.dimensions == 1536
    assert settings.llm.provider == "openrouter"
    assert settings.llm.model == "google/gemini-3-flash"
    assert settings.api.port == 8000


def test_settings_env_override():
    """Environment variables should override YAML values."""
    os.environ["LOOM_API__PORT"] = "9999"
    try:
        settings = LoomSettings()
        assert settings.api.port == 9999
    finally:
        del os.environ["LOOM_API__PORT"]
```

- [ ] **Step 5: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_settings.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'loom.settings'`

- [ ] **Step 6: Implement settings**

Create `src/loom/settings.py`:

```python
"""Application settings loaded from loom.yaml with env var overrides."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://loom:loom@localhost:5432/loom"


class EmbeddingConfig(BaseModel):
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536


class LLMConfig(BaseModel):
    provider: str = "openrouter"
    model: str = "google/gemini-3-flash"


class MCPTransportConfig(BaseModel):
    type: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8080


class MCPConfig(BaseModel):
    transports: list[MCPTransportConfig] = [MCPTransportConfig()]


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


def _yaml_settings(settings: BaseSettings) -> dict[str, Any]:
    """Load settings from loom.yaml if it exists."""
    yaml_path = Path("loom.yaml")
    if yaml_path.exists():
        with open(yaml_path) as f:
            return yaml.safe_load(f) or {}
    return {}


class LoomSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LOOM_",
        env_nested_delimiter="__",
    )

    database: DatabaseConfig = DatabaseConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    llm: LLMConfig = LLMConfig()
    mcp: MCPConfig = MCPConfig()
    api: APIConfig = APIConfig()

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):  # type: ignore[override]
        from pydantic_settings import (
            EnvSettingsSource,
            InitSettingsSource,
        )

        return (
            InitSettingsSource(settings_cls, kwargs.get("init_settings", {})),
            EnvSettingsSource(
                settings_cls,
                env_prefix=settings_cls.model_config.get("env_prefix", ""),
                env_nested_delimiter=settings_cls.model_config.get(
                    "env_nested_delimiter", "__"
                ),
            ),
            _yaml_settings,
        )
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_settings.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add .gitignore docker-compose.yml loom.yaml src/loom/settings.py tests/
git commit -m "feat: add Docker Compose, YAML config, and pydantic-settings"
```

---

### Task 3: Database Engine & Alembic Setup

**Files:**
- Create: `src/loom/db/__init__.py`
- Create: `src/loom/db/engine.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`

- [ ] **Step 1: Create alembic.ini**

Run: `uv run alembic init alembic`

Then edit `alembic.ini` to remove the hardcoded `sqlalchemy.url` (we'll set it in `env.py`).

- [ ] **Step 2: Write the failing test for engine**

Create `tests/integration/__init__.py` (empty).
Create `tests/integration/test_db.py`:

```python
import asyncpg
import pytest


@pytest.mark.asyncio
async def test_database_connection():
    """Verify we can connect to the test database."""
    conn = await asyncpg.connect(
        "postgresql://loom:loom@localhost:5432/loom"
    )
    try:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_pgvector_extension():
    """Verify pgvector extension is available."""
    conn = await asyncpg.connect(
        "postgresql://loom:loom@localhost:5432/loom"
    )
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        result = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        assert result is True
    finally:
        await conn.close()
```

- [ ] **Step 3: Start the database**

Run: `docker compose up -d`
Expected: PostgreSQL container running on port 5432.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_db.py -v`
Expected: PASS — DB is reachable and pgvector is available.

- [ ] **Step 5: Implement db engine module**

Create `src/loom/db/__init__.py` (empty).
Create `src/loom/db/engine.py`:

```python
"""Database connection pool management."""

import asyncpg
from pgvector.asyncpg import register_vector


async def create_pool(database_url: str) -> asyncpg.Pool:
    """Create an asyncpg connection pool with pgvector support.

    The database_url should be a plain postgresql:// URL (not the
    SQLAlchemy async dialect URL).
    """
    # Strip the sqlalchemy dialect prefix if present
    url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    pool = await asyncpg.create_pool(url, min_size=2, max_size=10)
    assert pool is not None

    # Register pgvector type codec on each connection
    async with pool.acquire() as conn:
        await register_vector(conn)

    return pool
```

- [ ] **Step 6: Configure alembic/env.py for async**

Replace `alembic/env.py` with:

```python
"""Alembic migration environment — async mode with asyncpg."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from loom.db.tables import metadata
from loom.settings import LoomSettings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata

settings = LoomSettings()
config.set_main_option("sqlalchemy.url", settings.database.url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Note: This references `loom.db.tables` which doesn't exist yet. It will be created in Task 4.

- [ ] **Step 7: Commit**

```bash
git add src/loom/db/ alembic.ini alembic/ tests/integration/
git commit -m "feat: add asyncpg engine, Alembic async config, and DB integration tests"
```

---

### Task 4: Database Tables & First Migration

**Files:**
- Create: `src/loom/db/tables.py`
- Create: `alembic/versions/001_initial_schema.py` (auto-generated)

- [ ] **Step 1: Create SQLAlchemy Core table definitions**

Create `src/loom/db/tables.py`:

```python
"""SQLAlchemy Core table definitions for Alembic and query building."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", UUID, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("handle", Text, unique=True, nullable=False),
    Column("email", Text, unique=True, nullable=False),
    Column("api_key", Text, unique=True, nullable=False),
    Column("role", String(20), nullable=False, server_default="contributor"),
    Column("signing_public_key", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
)

categories = Table(
    "categories",
    metadata,
    Column("id", UUID, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("slug", Text, unique=True, nullable=False),
    Column("name", Text, nullable=False),
    Column("description", Text, nullable=True),
    Column("parent_id", UUID, ForeignKey("categories.id"), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
)

skills = Table(
    "skills",
    metadata,
    Column("id", UUID, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("slug", Text, unique=True, nullable=False),
    Column("name", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("category_id", UUID, ForeignKey("categories.id"), nullable=False),
    Column("tags", ARRAY(Text), nullable=False, server_default="{}"),
    Column("scope", String(20), nullable=False, server_default="community"),
    Column("version", Text, nullable=False),
    Column("author_id", UUID, ForeignKey("users.id"), nullable=False),
    Column("signature", Text, nullable=True),
    Column("trust_tier", String(20), nullable=False, server_default="experimental"),
    Column("cost_profile", String(20), nullable=False, server_default="free"),
    Column("cost_drivers", ARRAY(Text), nullable=False, server_default="{}"),
    Column("estimated_duration", String(20), nullable=False, server_default="fast"),
    Column("dependencies", JSONB, nullable=False, server_default="{}"),
    Column("eval_spec", JSONB, nullable=False, server_default="{}"),
    Column("extends", Text, nullable=True),
    Column("embedding", Vector(1536), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Index("idx_skills_category", "category_id"),
    Index("idx_skills_trust_tier", "trust_tier"),
    Index("idx_skills_scope", "scope"),
    Index("idx_skills_tags", "tags", postgresql_using="gin"),
)

skill_versions = Table(
    "skill_versions",
    metadata,
    Column("id", UUID, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("skill_id", UUID, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
    Column("version", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("dependencies", JSONB, nullable=False, server_default="{}"),
    Column("eval_spec", JSONB, nullable=False, server_default="{}"),
    Column("cost_profile", String(20), nullable=False, server_default="free"),
    Column("cost_drivers", ARRAY(Text), nullable=False, server_default="{}"),
    Column("estimated_duration", String(20), nullable=False, server_default="fast"),
    Column("extends", Text, nullable=True),
    Column("signature", Text, nullable=True),
    Column("author_id", UUID, ForeignKey("users.id"), nullable=False),
    Column("changelog", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    UniqueConstraint("skill_id", "version", name="uq_skill_versions_skill_version"),
    Index("idx_skill_versions_skill", "skill_id"),
)
```

- [ ] **Step 2: Generate the migration**

Run: `uv run alembic revision --autogenerate -m "initial schema"`

**Important:** After generation, manually edit the migration to add at the top of `upgrade()`:

```python
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

And at the bottom of `downgrade()`:

```python
op.execute("DROP EXTENSION IF EXISTS vector")
```

- [ ] **Step 3: Run the migration**

Run: `uv run alembic upgrade head`
Expected: All tables created successfully.

- [ ] **Step 4: Verify tables exist**

Run: `docker compose exec db psql -U loom -c "\dt"`
Expected: Lists `users`, `categories`, `skills`, `skill_versions`, `alembic_version`.

- [ ] **Step 5: Commit**

```bash
git add src/loom/db/tables.py alembic/
git commit -m "feat: add database schema and initial migration"
```

---

### Task 5: Pre-commit & CI Config

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Create pre-commit config**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.10
          - pydantic-settings>=2.7
        args: [--config-file=pyproject.toml]
        pass_filenames: false
```

- [ ] **Step 2: Install pre-commit hooks**

Run: `uv run pre-commit install`
Expected: Hooks installed.

- [ ] **Step 3: Verify hooks work**

Run: `uv run pre-commit run --all-files`
Expected: All checks pass.

- [ ] **Step 4: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "feat: add pre-commit hooks for ruff and mypy"
```

---

## Chunk 2: Domain Models

### Task 6: Common Types & Enums

**Files:**
- Create: `src/loom/models/__init__.py`
- Create: `src/loom/models/common.py`
- Test: `tests/unit/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_models.py`:

```python
from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EstimatedDuration,
    MCPServerDependency,
    PrivacyImpact,
    Scope,
    TrustRequirements,
    TrustTier,
)


def test_trust_tier_ordering():
    """Trust tiers should be comparable for floor checks."""
    assert TrustTier.EXPERIMENTAL.rank < TrustTier.COMMUNITY.rank
    assert TrustTier.COMMUNITY.rank < TrustTier.VERIFIED.rank


def test_trust_tier_meets_floor():
    assert TrustTier.VERIFIED.meets_floor(TrustTier.COMMUNITY)
    assert TrustTier.COMMUNITY.meets_floor(TrustTier.COMMUNITY)
    assert not TrustTier.EXPERIMENTAL.meets_floor(TrustTier.COMMUNITY)


def test_cost_profile_within_budget():
    assert CostProfile.FREE.within_budget(CostProfile.LOW)
    assert CostProfile.LOW.within_budget(CostProfile.LOW)
    assert not CostProfile.HIGH.within_budget(CostProfile.LOW)


def test_privacy_impact_defaults():
    """Unknown should be the safe default."""
    pi = PrivacyImpact()
    assert pi.external_data_sharing is False
    assert pi.input_logging == "unknown"
    assert pi.data_retention == "unknown"


def test_dependency_declaration_roundtrip():
    """Dependency declarations should serialize and deserialize from JSONB."""
    dep = DependencyDeclaration(
        mcp_servers=[
            MCPServerDependency(uri="filesystem", required=True, scopes=["read"]),
        ],
        trust_requirements=TrustRequirements(
            data_classification="none",
            network_access=False,
            privacy_impact=PrivacyImpact(external_data_sharing=False),
        ),
    )
    data = dep.model_dump()
    restored = DependencyDeclaration.model_validate(data)
    assert restored.mcp_servers[0].uri == "filesystem"
    assert restored.trust_requirements.privacy_impact.external_data_sharing is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement common models**

Create `src/loom/models/__init__.py` (empty).
Create `src/loom/models/common.py`:

```python
"""Shared domain types used across skills, capabilities, and resolution."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel


class TrustTier(str, Enum):
    EXPERIMENTAL = "experimental"
    COMMUNITY = "community"
    VERIFIED = "verified"

    @property
    def rank(self) -> int:
        return {
            TrustTier.EXPERIMENTAL: 0,
            TrustTier.COMMUNITY: 1,
            TrustTier.VERIFIED: 2,
        }[self]

    def meets_floor(self, floor: "TrustTier") -> bool:
        return self.rank >= floor.rank


class CostProfile(str, Enum):
    FREE = "free"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

    @property
    def rank(self) -> int:
        return {
            CostProfile.FREE: 0,
            CostProfile.LOW: 1,
            CostProfile.MODERATE: 2,
            CostProfile.HIGH: 3,
        }[self]

    def within_budget(self, budget: "CostProfile") -> bool:
        return self.rank <= budget.rank


class EstimatedDuration(str, Enum):
    FAST = "fast"
    MODERATE = "moderate"
    SLOW = "slow"


class Scope(str, Enum):
    COMMUNITY = "community"
    CORPORATE = "corporate"


class PrivacyImpact(BaseModel):
    external_data_sharing: bool = False
    input_logging: Literal["none", "anonymised", "full", "unknown"] = "unknown"
    data_retention: Literal["none", "transient", "persistent", "unknown"] = "unknown"


class TrustRequirements(BaseModel):
    data_classification: Literal["none", "internal", "confidential"] = "none"
    network_access: bool = False
    privacy_impact: PrivacyImpact = PrivacyImpact()


class MCPServerDependency(BaseModel):
    uri: str
    required: bool = True
    scopes: list[str] = []


class APIDependency(BaseModel):
    name: str
    auth_type: str = "api_key"
    scopes: list[str] = []


class DependencyDeclaration(BaseModel):
    mcp_servers: list[MCPServerDependency] = []
    apis: list[APIDependency] = []
    trust_requirements: TrustRequirements = TrustRequirements()


class EvalScenario(BaseModel):
    description: str
    input_context: str
    success_criteria: str


class QualityDimension(BaseModel):
    name: str
    description: str


class EvalSpec(BaseModel):
    scenarios: list[EvalScenario] = []
    quality_dimensions: list[QualityDimension] = []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/models/ tests/unit/test_models.py
git commit -m "feat: add common domain types — enums, dependencies, privacy"
```

---

### Task 7: Skill & Category Models

**Files:**
- Create: `src/loom/models/skill.py`
- Create: `src/loom/models/category.py`
- Create: `src/loom/models/user.py`
- Test: `tests/unit/test_skill_model.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_skill_model.py`:

```python
import uuid

from loom.models.common import CostProfile, DependencyDeclaration, EvalSpec, TrustTier
from loom.models.skill import Skill, SkillCreate


def test_skill_create_minimal():
    """SkillCreate should accept minimal required fields."""
    skill = SkillCreate(
        slug="test-skill",
        name="Test Skill",
        description="A test skill",
        content="# Test\nDo the thing.",
        category_slug="development/git",
        version="1.0.0",
    )
    assert skill.slug == "test-skill"
    assert skill.trust_tier == TrustTier.EXPERIMENTAL
    assert skill.cost_profile == CostProfile.FREE


def test_skill_create_full():
    """SkillCreate should accept all optional fields."""
    skill = SkillCreate(
        slug="full-skill",
        name="Full Skill",
        description="A fully specified skill",
        content="# Full\nDo everything.",
        category_slug="development/git",
        version="1.0.0",
        tags=["git", "commits"],
        cost_profile=CostProfile.LOW,
        cost_drivers=["LLM API call"],
        estimated_duration="moderate",
        dependencies=DependencyDeclaration(),
        eval_spec=EvalSpec(),
        extends="loom://base-skill@1.0.0",
    )
    assert skill.tags == ["git", "commits"]
    assert skill.extends == "loom://base-skill@1.0.0"


def test_skill_model():
    """Skill (read model) includes server-generated fields."""
    skill = Skill(
        id=uuid.uuid4(),
        slug="test-skill",
        name="Test Skill",
        description="A test skill",
        content="# Test",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=TrustTier.EXPERIMENTAL,
        cost_profile=CostProfile.FREE,
        cost_drivers=[],
        estimated_duration="fast",
        dependencies={},
        eval_spec={},
    )
    assert skill.signature is None
    assert skill.extends is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_skill_model.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement models**

Create `src/loom/models/user.py`:

```python
"""User domain models."""

import uuid as uuid_mod
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class User(BaseModel):
    id: uuid_mod.UUID
    handle: str
    email: str
    role: Literal["contributor", "steward", "maintainer"] = "contributor"
    signing_public_key: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserCreate(BaseModel):
    handle: str
    email: str
    role: Literal["contributor", "steward", "maintainer"] = "contributor"
```

Create `src/loom/models/category.py`:

```python
"""Category domain models."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel


class Category(BaseModel):
    id: uuid_mod.UUID
    slug: str
    name: str
    description: str | None = None
    parent_id: uuid_mod.UUID | None = None
    created_at: datetime | None = None


class CategoryCreate(BaseModel):
    slug: str
    name: str
    description: str | None = None
    parent_id: uuid_mod.UUID | None = None
```

Create `src/loom/models/skill.py`:

```python
"""Skill domain models."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel

from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EstimatedDuration,
    EvalSpec,
    Scope,
    TrustTier,
)


class SkillCreate(BaseModel):
    """Input model for creating a skill."""

    slug: str
    name: str
    description: str
    content: str
    category_slug: str
    version: str
    tags: list[str] = []
    scope: Scope = Scope.COMMUNITY
    trust_tier: TrustTier = TrustTier.EXPERIMENTAL
    cost_profile: CostProfile = CostProfile.FREE
    cost_drivers: list[str] = []
    estimated_duration: EstimatedDuration | str = EstimatedDuration.FAST
    dependencies: DependencyDeclaration = DependencyDeclaration()
    eval_spec: EvalSpec = EvalSpec()
    extends: str | None = None


class Skill(BaseModel):
    """Full skill as stored and returned from DB."""

    id: uuid_mod.UUID
    slug: str
    name: str
    description: str
    content: str
    category_id: uuid_mod.UUID
    tags: list[str]
    scope: str
    version: str
    author_id: uuid_mod.UUID
    trust_tier: TrustTier
    cost_profile: CostProfile
    cost_drivers: list[str]
    estimated_duration: str
    dependencies: dict  # type: ignore[type-arg]
    eval_spec: dict  # type: ignore[type-arg]
    signature: str | None = None
    extends: str | None = None
    embedding: list[float] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SkillSummary(BaseModel):
    """Lightweight skill metadata for search results (no full content)."""

    id: uuid_mod.UUID
    slug: str
    name: str
    description: str
    category_id: uuid_mod.UUID
    tags: list[str]
    version: str
    trust_tier: TrustTier
    cost_profile: CostProfile
    estimated_duration: str


class SkillVersion(BaseModel):
    """A historical version of a skill."""

    id: uuid_mod.UUID
    skill_id: uuid_mod.UUID
    version: str
    content: str
    dependencies: dict  # type: ignore[type-arg]
    eval_spec: dict  # type: ignore[type-arg]
    cost_profile: str
    cost_drivers: list[str]
    estimated_duration: str
    extends: str | None = None
    signature: str | None = None
    author_id: uuid_mod.UUID
    changelog: str | None = None
    created_at: datetime | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_skill_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/models/ tests/unit/test_skill_model.py
git commit -m "feat: add Skill, Category, and User domain models"
```

---

### Task 8: Resolution Models

**Files:**
- Create: `src/loom/models/resolution.py`
- Test: `tests/unit/test_resolution_model.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_resolution_model.py`:

```python
import uuid

from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import (
    Alternative,
    RejectedCandidate,
    ResolutionContext,
    ResolutionError,
    ResolvedSkill,
)
from loom.models.skill import Skill


def _make_skill(**overrides) -> Skill:  # type: ignore[no-untyped-def]
    defaults = dict(
        id=uuid.uuid4(),
        slug="test-skill",
        name="Test",
        description="Test skill",
        content="# Test",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=TrustTier.EXPERIMENTAL,
        cost_profile=CostProfile.FREE,
        cost_drivers=[],
        estimated_duration="fast",
        dependencies={},
        eval_spec={},
    )
    defaults.update(overrides)
    return Skill(**defaults)


def test_resolution_context_minimal():
    ctx = ResolutionContext()
    assert ctx.trust_floor is None
    assert ctx.available_tools == []


def test_resolution_context_full():
    ctx = ResolutionContext(
        trust_floor=TrustTier.COMMUNITY,
        cost_budget=CostProfile.LOW,
        available_tools=["filesystem", "git"],
    )
    assert ctx.trust_floor == TrustTier.COMMUNITY
    assert "git" in ctx.available_tools


def test_resolved_skill():
    skill = _make_skill()
    resolved = ResolvedSkill(
        skill=skill,
        dependencies_satisfied=["filesystem"],
        dependencies_missing=["github-api"],
        alternatives=[],
        rejected_candidates=[],
        selection_rationale=["Matched task", "All deps met"],
    )
    assert resolved.skill.slug == "test-skill"
    assert "Matched task" in resolved.selection_rationale


def test_resolution_error():
    err = ResolutionError(
        error="no_match",
        message="No skills found",
        suggestions=["Try broader terms"],
    )
    assert err.error == "no_match"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_resolution_model.py -v`
Expected: FAIL

- [ ] **Step 3: Implement resolution models**

Create `src/loom/models/resolution.py`:

```python
"""Resolution domain models — the core resolve() interface."""

from pydantic import BaseModel

from loom.models.common import CostProfile, TrustTier
from loom.models.skill import Skill, SkillSummary


class ResolutionContext(BaseModel):
    """Runtime context that shapes resolution."""

    trust_floor: TrustTier | None = None
    cost_budget: CostProfile | None = None
    latency_budget: str | None = None
    data_classification: str | None = None
    available_tools: list[str] = []
    approved_providers: list[str] = []
    runtime: str | None = None


class Alternative(BaseModel):
    """A ranked alternative to the best match."""

    skill: SkillSummary
    match_score: float
    tradeoff: str


class RejectedCandidate(BaseModel):
    """A near-match that was filtered out."""

    skill: SkillSummary
    reason: str


class ResolvedSkill(BaseModel):
    """The full resolution response."""

    skill: Skill
    dependencies_satisfied: list[str] = []
    dependencies_missing: list[str] = []
    alternatives: list[Alternative] = []
    rejected_candidates: list[RejectedCandidate] = []
    selection_rationale: list[str] = []


class ResolutionError(BaseModel):
    """Structured error when resolution fails."""

    error: str  # no_match | trust_floor_not_met | deprecated | removed
    message: str
    suggestions: list[str] | None = None
    available_at_lower_tier: list[SkillSummary] | None = None
    successor: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_resolution_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/models/resolution.py tests/unit/test_resolution_model.py
git commit -m "feat: add resolution models — context, resolved skill, errors"
```

---

## Chunk 3: Providers & Repositories

### Task 9: Embedding & LLM Providers

**Files:**
- Create: `src/loom/providers/__init__.py`
- Create: `src/loom/providers/embeddings.py`
- Create: `src/loom/providers/llm.py`
- Test: `tests/unit/test_providers.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_providers.py`:

```python
from loom.providers.embeddings import create_embedder
from loom.providers.llm import create_llm_model
from loom.settings import EmbeddingConfig, LLMConfig


def test_create_embedder_returns_embedder():
    """Factory should return a pydantic-ai Embedder instance."""
    config = EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
        dimensions=1536,
    )
    # We can't call embed without a real API key, but we can verify construction
    embedder = create_embedder(config)
    assert embedder is not None


def test_create_llm_model_openrouter():
    """Factory should return an OpenRouter model."""
    config = LLMConfig(
        provider="openrouter",
        model="google/gemini-3-flash",
    )
    model = create_llm_model(config)
    assert model is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_providers.py -v`
Expected: FAIL

- [ ] **Step 3: Implement providers**

Create `src/loom/providers/__init__.py` (empty).
Create `src/loom/providers/embeddings.py`:

```python
"""Embedding provider factory — config to pydantic-ai Embedder."""

import os

from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.providers.openai import OpenAIProvider

from loom.settings import EmbeddingConfig


def create_embedder(config: EmbeddingConfig) -> Embedder:
    """Create a pydantic-ai Embedder from config.

    Currently supports OpenAI and OpenAI-compatible providers.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")

    if config.provider == "openai":
        model = OpenAIEmbeddingModel(
            config.model,
            provider=OpenAIProvider(api_key=api_key),
        )
    else:
        # For any OpenAI-compatible provider, use base_url
        base_url = getattr(config, "base_url", None)
        model = OpenAIEmbeddingModel(
            config.model,
            provider=OpenAIProvider(api_key=api_key, base_url=base_url or ""),
        )

    settings = EmbeddingSettings(dimensions=config.dimensions) if config.dimensions else None
    return Embedder(model, settings=settings)
```

Create `src/loom/providers/llm.py`:

```python
"""LLM provider factory — config to pydantic-ai model."""

import os

from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from loom.settings import LLMConfig


def create_llm_model(config: LLMConfig) -> OpenRouterModel:
    """Create a pydantic-ai model from config.

    Currently supports OpenRouter. Extend for other providers as needed.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "")

    if config.provider == "openrouter":
        return OpenRouterModel(
            config.model,
            provider=OpenRouterProvider(api_key=api_key),
        )

    raise ValueError(f"Unsupported LLM provider: {config.provider}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_providers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/providers/ tests/unit/test_providers.py
git commit -m "feat: add embedding and LLM provider factories"
```

---

### Task 10: Category Repository

**Files:**
- Create: `src/loom/db/repositories/__init__.py`
- Create: `src/loom/db/repositories/category_repo.py`
- Test: `tests/integration/test_category_repo.py`

- [ ] **Step 1: Create test fixtures**

Create `tests/conftest.py`:

```python
"""Shared test fixtures."""

from collections.abc import AsyncIterator

import asyncpg
import pytest


@pytest.fixture(scope="session")
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    """Create a connection pool to the test database."""
    pool = await asyncpg.create_pool(
        "postgresql://loom:loom@localhost:5432/loom",
        min_size=1,
        max_size=5,
    )
    assert pool is not None
    yield pool
    await pool.close()


@pytest.fixture
async def db_conn(db_pool: asyncpg.Pool) -> AsyncIterator[asyncpg.Connection]:
    """Get a connection and wrap test in a transaction that rolls back."""
    async with db_pool.acquire() as conn:
        tx = conn.transaction()
        await tx.start()
        yield conn
        await tx.rollback()
```

- [ ] **Step 2: Write the failing test**

Create `tests/integration/test_category_repo.py`:

```python
import asyncpg
import pytest

from loom.db.repositories.category_repo import CategoryRepo
from loom.models.category import CategoryCreate


@pytest.mark.asyncio
async def test_create_and_get_category(db_conn: asyncpg.Connection):
    repo = CategoryRepo(db_conn)
    created = await repo.create(
        CategoryCreate(slug="development", name="Development", description="Dev skills")
    )
    assert created.slug == "development"
    assert created.id is not None

    fetched = await repo.get_by_slug("development")
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_list_categories(db_conn: asyncpg.Connection):
    repo = CategoryRepo(db_conn)
    await repo.create(CategoryCreate(slug="dev", name="Dev"))
    await repo.create(CategoryCreate(slug="docs", name="Docs"))
    cats = await repo.list_all()
    assert len(cats) >= 2


@pytest.mark.asyncio
async def test_create_child_category(db_conn: asyncpg.Connection):
    repo = CategoryRepo(db_conn)
    parent = await repo.create(CategoryCreate(slug="development", name="Development"))
    child = await repo.create(
        CategoryCreate(slug="development/git", name="Git", parent_id=parent.id)
    )
    assert child.parent_id == parent.id
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_category_repo.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement category repo**

Create `src/loom/db/repositories/__init__.py` (empty).
Create `src/loom/db/repositories/category_repo.py`:

```python
"""Category data access — all SQL lives here."""

import uuid as uuid_mod

import asyncpg

from loom.models.category import Category, CategoryCreate


class CategoryRepo:
    def __init__(self, conn: asyncpg.Connection | asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, data: CategoryCreate) -> Category:
        row = await self._conn.fetchrow(
            """
            INSERT INTO categories (slug, name, description, parent_id)
            VALUES ($1, $2, $3, $4)
            RETURNING id, slug, name, description, parent_id, created_at
            """,
            data.slug,
            data.name,
            data.description,
            data.parent_id,
        )
        return Category(**dict(row))

    async def get_by_slug(self, slug: str) -> Category | None:
        row = await self._conn.fetchrow(
            "SELECT id, slug, name, description, parent_id, created_at FROM categories WHERE slug = $1",
            slug,
        )
        if row is None:
            return None
        return Category(**dict(row))

    async def get_by_id(self, category_id: uuid_mod.UUID) -> Category | None:
        row = await self._conn.fetchrow(
            "SELECT id, slug, name, description, parent_id, created_at FROM categories WHERE id = $1",
            category_id,
        )
        if row is None:
            return None
        return Category(**dict(row))

    async def list_all(self) -> list[Category]:
        rows = await self._conn.fetch(
            "SELECT id, slug, name, description, parent_id, created_at FROM categories ORDER BY slug"
        )
        return [Category(**dict(row)) for row in rows]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_category_repo.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/loom/db/repositories/ tests/conftest.py tests/integration/test_category_repo.py
git commit -m "feat: add CategoryRepo with CRUD operations"
```

---

### Task 11: Skill Repository

**Files:**
- Create: `src/loom/db/repositories/skill_repo.py`
- Test: `tests/integration/test_skill_repo.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_skill_repo.py`:

```python
import asyncpg
import pytest

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.category import CategoryCreate
from loom.models.common import CostProfile, TrustTier


@pytest.fixture
async def setup_data(db_conn: asyncpg.Connection):
    """Create a user and category for skill tests."""
    # Create a test user
    user_row = await db_conn.fetchrow(
        """
        INSERT INTO users (handle, email, api_key, role)
        VALUES ('testuser', 'test@example.com', 'test-key-hash', 'contributor')
        RETURNING id
        """
    )
    user_id = user_row["id"]

    # Create a category
    cat_repo = CategoryRepo(db_conn)
    category = await cat_repo.create(CategoryCreate(slug="development/git", name="Git"))

    return {"user_id": user_id, "category_id": category.id}


@pytest.mark.asyncio
async def test_create_and_get_skill(db_conn: asyncpg.Connection, setup_data):
    repo = SkillRepo(db_conn)
    skill = await repo.create(
        slug="git-commit-conventional",
        name="Conventional Commit",
        description="Create conventional git commits",
        content="# Conventional Commit\nFollow the spec...",
        category_id=setup_data["category_id"],
        tags=["git", "commits"],
        version="1.0.0",
        author_id=setup_data["user_id"],
        dependencies={},
        eval_spec={},
    )
    assert skill.slug == "git-commit-conventional"
    assert skill.trust_tier == TrustTier.EXPERIMENTAL

    fetched = await repo.get_by_slug("git-commit-conventional")
    assert fetched is not None
    assert fetched.id == skill.id


@pytest.mark.asyncio
async def test_get_by_slug_with_version(db_conn: asyncpg.Connection, setup_data):
    repo = SkillRepo(db_conn)
    await repo.create(
        slug="versioned-skill",
        name="Versioned",
        description="A versioned skill",
        content="# V1",
        category_id=setup_data["category_id"],
        tags=[],
        version="1.0.0",
        author_id=setup_data["user_id"],
        dependencies={},
        eval_spec={},
    )
    # Version lookup queries skill_versions table
    fetched = await repo.get_by_slug("versioned-skill", version="1.0.0")
    assert fetched is not None
    assert fetched.version == "1.0.0"


@pytest.mark.asyncio
async def test_vector_search(db_conn: asyncpg.Connection, setup_data):
    repo = SkillRepo(db_conn)
    # Create a skill with a known embedding
    fake_embedding = [0.1] * 1536
    await repo.create(
        slug="searchable-skill",
        name="Searchable",
        description="A searchable skill",
        content="# Searchable",
        category_id=setup_data["category_id"],
        tags=[],
        version="1.0.0",
        author_id=setup_data["user_id"],
        dependencies={},
        eval_spec={},
        embedding=fake_embedding,
    )

    # Search with a similar embedding
    results = await repo.vector_search(fake_embedding, limit=5)
    assert len(results) >= 1
    assert results[0].slug == "searchable-skill"


@pytest.mark.asyncio
async def test_list_skills(db_conn: asyncpg.Connection, setup_data):
    repo = SkillRepo(db_conn)
    await repo.create(
        slug="skill-a",
        name="Skill A",
        description="First",
        content="# A",
        category_id=setup_data["category_id"],
        tags=["a"],
        version="1.0.0",
        author_id=setup_data["user_id"],
        dependencies={},
        eval_spec={},
    )
    await repo.create(
        slug="skill-b",
        name="Skill B",
        description="Second",
        content="# B",
        category_id=setup_data["category_id"],
        tags=["b"],
        version="1.0.0",
        author_id=setup_data["user_id"],
        dependencies={},
        eval_spec={},
    )
    skills = await repo.list_all()
    assert len(skills) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_skill_repo.py -v`
Expected: FAIL

- [ ] **Step 3: Implement skill repo**

Create `src/loom/db/repositories/skill_repo.py`:

```python
"""Skill data access — all SQL lives here."""

import uuid as uuid_mod

import asyncpg

from loom.models.skill import Skill, SkillSummary, SkillVersion


class SkillRepo:
    def __init__(self, conn: asyncpg.Connection | asyncpg.Pool) -> None:
        self._conn = conn

    async def create(
        self,
        *,
        slug: str,
        name: str,
        description: str,
        content: str,
        category_id: uuid_mod.UUID,
        tags: list[str],
        version: str,
        author_id: uuid_mod.UUID,
        dependencies: dict,  # type: ignore[type-arg]
        eval_spec: dict,  # type: ignore[type-arg]
        scope: str = "community",
        cost_profile: str = "free",
        cost_drivers: list[str] | None = None,
        estimated_duration: str = "fast",
        extends: str | None = None,
        embedding: list[float] | None = None,
    ) -> Skill:
        row = await self._conn.fetchrow(
            """
            INSERT INTO skills (
                slug, name, description, content, category_id, tags, scope,
                version, author_id, cost_profile, cost_drivers, estimated_duration,
                dependencies, eval_spec, extends, embedding
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7,
                $8, $9, $10, $11, $12,
                $13, $14, $15, $16
            )
            RETURNING *
            """,
            slug, name, description, content, category_id, tags, scope,
            version, author_id, cost_profile, cost_drivers or [], estimated_duration,
            dependencies, eval_spec, extends, embedding,
        )
        return self._row_to_skill(row)

    async def create_version(
        self,
        *,
        skill_id: uuid_mod.UUID,
        version: str,
        content: str,
        dependencies: dict,  # type: ignore[type-arg]
        eval_spec: dict,  # type: ignore[type-arg]
        author_id: uuid_mod.UUID,
        cost_profile: str = "free",
        cost_drivers: list[str] | None = None,
        estimated_duration: str = "fast",
        extends: str | None = None,
        changelog: str | None = None,
    ) -> SkillVersion:
        row = await self._conn.fetchrow(
            """
            INSERT INTO skill_versions (
                skill_id, version, content, dependencies, eval_spec,
                cost_profile, cost_drivers, estimated_duration, extends,
                author_id, changelog
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING *
            """,
            skill_id, version, content, dependencies,
            eval_spec, cost_profile, cost_drivers or [],
            estimated_duration, extends, author_id, changelog,
        )
        return SkillVersion(**dict(row))

    async def get_by_slug(
        self, slug: str, version: str | None = None
    ) -> Skill | None:
        if version:
            # Look up a specific version from skill_versions
            row = await self._conn.fetchrow(
                """
                SELECT s.id, s.slug, s.name, s.description, s.category_id,
                       s.tags, s.scope, s.author_id, s.signature, s.trust_tier,
                       s.embedding, s.created_at, s.updated_at,
                       sv.version, sv.content, sv.dependencies, sv.eval_spec,
                       sv.cost_profile, sv.cost_drivers, sv.estimated_duration,
                       sv.extends
                FROM skills s
                JOIN skill_versions sv ON sv.skill_id = s.id
                WHERE s.slug = $1 AND sv.version = $2
                """,
                slug, version,
            )
            if row is None:
                return None
            return self._row_to_skill(row)

        row = await self._conn.fetchrow(
            "SELECT * FROM skills WHERE slug = $1", slug
        )
        if row is None:
            return None
        return self._row_to_skill(row)

    async def get_by_id(self, skill_id: uuid_mod.UUID) -> Skill | None:
        row = await self._conn.fetchrow("SELECT * FROM skills WHERE id = $1", skill_id)
        if row is None:
            return None
        return self._row_to_skill(row)

    async def list_all(
        self,
        category_id: uuid_mod.UUID | None = None,
        trust_tier: str | None = None,
    ) -> list[SkillSummary]:
        query = "SELECT * FROM skills WHERE 1=1"
        params: list = []
        idx = 1

        if category_id:
            query += f" AND category_id = ${idx}"
            params.append(category_id)
            idx += 1
        if trust_tier:
            query += f" AND trust_tier = ${idx}"
            params.append(trust_tier)
            idx += 1

        query += " ORDER BY name"
        rows = await self._conn.fetch(query, *params)
        return [self._row_to_summary(row) for row in rows]

    async def vector_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        category_id: uuid_mod.UUID | None = None,
        trust_tier: str | None = None,
    ) -> list[Skill]:
        """Find skills by vector similarity. Returns skills ordered by distance."""
        query = """
            SELECT *, embedding <=> $1::vector AS distance
            FROM skills
            WHERE embedding IS NOT NULL
        """
        params: list = [query_embedding]
        idx = 2

        if category_id:
            query += f" AND category_id = ${idx}"
            params.append(category_id)
            idx += 1
        if trust_tier:
            query += f" AND trust_tier = ${idx}"
            params.append(trust_tier)
            idx += 1

        query += f" ORDER BY distance LIMIT ${idx}"
        params.append(limit)

        rows = await self._conn.fetch(query, *params)
        return [self._row_to_skill(row) for row in rows]

    def _row_to_skill(self, row: asyncpg.Record) -> Skill:
        d = dict(row)
        # Remove distance column if present (from vector search)
        d.pop("distance", None)
        return Skill(**d)

    def _row_to_summary(self, row: asyncpg.Record) -> SkillSummary:
        d = dict(row)
        return SkillSummary(
            id=d["id"],
            slug=d["slug"],
            name=d["name"],
            description=d["description"],
            category_id=d["category_id"],
            tags=d["tags"],
            version=d["version"],
            trust_tier=d["trust_tier"],
            cost_profile=d["cost_profile"],
            estimated_duration=d["estimated_duration"],
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_skill_repo.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/db/repositories/skill_repo.py tests/integration/test_skill_repo.py
git commit -m "feat: add SkillRepo with CRUD and vector search"
```

---

## Chunk 4: Services

### Task 12: EvalService (Structural Validation Stub)

**Files:**
- Create: `src/loom/services/__init__.py`
- Create: `src/loom/services/eval.py`
- Test: `tests/unit/test_eval_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_eval_service.py`:

```python
from loom.models.common import EvalScenario, EvalSpec, QualityDimension
from loom.services.eval import EvalService, ValidationResult


def test_valid_skill_passes():
    svc = EvalService()
    result = svc.validate_structure(
        content="# A real skill\nDo the thing step by step.",
        dependencies={"mcp_servers": [], "apis": [], "trust_requirements": {}},
        eval_spec=EvalSpec(
            scenarios=[EvalScenario(
                description="Basic use",
                input_context="Normal",
                success_criteria="Works",
            )],
            quality_dimensions=[QualityDimension(name="clarity", description="Clear")],
        ).model_dump(),
    )
    assert result.passed


def test_empty_content_fails():
    svc = EvalService()
    result = svc.validate_structure(content="", dependencies={}, eval_spec={})
    assert not result.passed
    assert any("content" in e.lower() for e in result.errors)


def test_missing_eval_scenarios_fails():
    svc = EvalService()
    result = svc.validate_structure(
        content="# Real content",
        dependencies={},
        eval_spec={"scenarios": [], "quality_dimensions": []},
    )
    assert not result.passed
    assert any("scenario" in e.lower() for e in result.errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_eval_service.py -v`
Expected: FAIL

- [ ] **Step 3: Implement eval service**

Create `src/loom/services/__init__.py` (empty).
Create `src/loom/services/eval.py`:

```python
"""Structural validation for skills — M1 stub of the full eval engine.

In M2 this gains LLM-powered quality scoring, 3-run median, tolerance bands.
For M1, only deterministic structural checks.
"""

from pydantic import BaseModel


class ValidationResult(BaseModel):
    passed: bool
    errors: list[str] = []
    warnings: list[str] = []


class EvalService:
    """Structural validation of skill content and metadata.

    M1 scope: deterministic checks only. No LLM scoring.
    """

    MIN_CONTENT_LENGTH = 10

    def validate_structure(
        self,
        content: str,
        dependencies: dict,  # type: ignore[type-arg]
        eval_spec: dict,  # type: ignore[type-arg]
    ) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        # Content checks
        if not content or not content.strip():
            errors.append("Content must not be empty")
        elif len(content.strip()) < self.MIN_CONTENT_LENGTH:
            errors.append(
                f"Content too short (minimum {self.MIN_CONTENT_LENGTH} characters)"
            )

        # Eval spec checks
        scenarios = eval_spec.get("scenarios", [])
        if not scenarios:
            errors.append("At least one eval scenario is required")

        dimensions = eval_spec.get("quality_dimensions", [])
        if not dimensions:
            warnings.append("No quality dimensions defined — scoring will be limited")

        # Dependency structure checks
        if dependencies:
            mcp_servers = dependencies.get("mcp_servers", [])
            for server in mcp_servers:
                if not isinstance(server, dict) or "uri" not in server:
                    errors.append("Each MCP server dependency must have a 'uri' field")

        return ValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_eval_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/services/ tests/unit/test_eval_service.py
git commit -m "feat: add EvalService with structural validation (M1 stub)"
```

---

### Task 13: RegistryService

**Files:**
- Create: `src/loom/services/registry.py`
- Test: `tests/integration/test_registry_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_registry_service.py`:

```python
import asyncpg
import pytest

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.category import CategoryCreate
from loom.models.common import EvalScenario, EvalSpec, QualityDimension
from loom.models.skill import SkillCreate
from loom.services.eval import EvalService
from loom.services.registry import RegistryService


@pytest.fixture
async def registry(db_conn: asyncpg.Connection):
    skill_repo = SkillRepo(db_conn)
    category_repo = CategoryRepo(db_conn)
    eval_svc = EvalService()

    # Create a category
    await category_repo.create(CategoryCreate(slug="development/git", name="Git"))

    # Create a user
    await db_conn.execute(
        """
        INSERT INTO users (handle, email, api_key, role)
        VALUES ('testuser', 'test@example.com', 'test-key', 'contributor')
        """
    )
    user = await db_conn.fetchrow("SELECT id FROM users WHERE handle = 'testuser'")

    return RegistryService(
        skill_repo=skill_repo,
        category_repo=category_repo,
        eval_service=eval_svc,
    ), user["id"]


@pytest.mark.asyncio
async def test_create_skill_succeeds(registry):
    svc, user_id = registry
    skill = await svc.create_skill(
        data=SkillCreate(
            slug="test-skill",
            name="Test Skill",
            description="A test skill",
            content="# Test Skill\nDo the thing step by step with detail.",
            category_slug="development/git",
            version="1.0.0",
            eval_spec=EvalSpec(
                scenarios=[EvalScenario(
                    description="Basic", input_context="Normal", success_criteria="Works"
                )],
                quality_dimensions=[QualityDimension(name="clarity", description="Clear")],
            ),
        ),
        author_id=user_id,
    )
    assert skill.slug == "test-skill"
    assert skill.version == "1.0.0"


@pytest.mark.asyncio
async def test_create_skill_fails_validation(registry):
    svc, user_id = registry
    with pytest.raises(ValueError, match="Structural validation failed"):
        await svc.create_skill(
            data=SkillCreate(
                slug="bad-skill",
                name="Bad",
                description="Bad",
                content="",
                category_slug="development/git",
                version="1.0.0",
            ),
            author_id=user_id,
        )


@pytest.mark.asyncio
async def test_create_skill_unknown_category(registry):
    svc, user_id = registry
    with pytest.raises(ValueError, match="Category not found"):
        await svc.create_skill(
            data=SkillCreate(
                slug="orphan",
                name="Orphan",
                description="No category",
                content="# Content with enough length for validation to pass",
                category_slug="nonexistent/category",
                version="1.0.0",
                eval_spec=EvalSpec(
                    scenarios=[EvalScenario(
                        description="X", input_context="Y", success_criteria="Z"
                    )],
                    quality_dimensions=[QualityDimension(name="c", description="d")],
                ),
            ),
            author_id=user_id,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_registry_service.py -v`
Expected: FAIL

- [ ] **Step 3: Implement registry service**

Create `src/loom/services/registry.py`:

```python
"""Registry service — skill CRUD, versioning, and format validation."""

import uuid as uuid_mod

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.skill import Skill, SkillCreate, SkillSummary
from loom.services.eval import EvalService


class RegistryService:
    def __init__(
        self,
        skill_repo: SkillRepo,
        category_repo: CategoryRepo,
        eval_service: EvalService,
    ) -> None:
        self._skills = skill_repo
        self._categories = category_repo
        self._eval = eval_service

    async def create_skill(
        self,
        data: SkillCreate,
        author_id: uuid_mod.UUID,
        embedding: list[float] | None = None,
    ) -> Skill:
        # Validate structure
        result = self._eval.validate_structure(
            content=data.content,
            dependencies=data.dependencies.model_dump() if hasattr(data.dependencies, 'model_dump') else data.dependencies,
            eval_spec=data.eval_spec.model_dump() if hasattr(data.eval_spec, 'model_dump') else data.eval_spec,
        )
        if not result.passed:
            raise ValueError(f"Structural validation failed: {'; '.join(result.errors)}")

        # Resolve category
        category = await self._categories.get_by_slug(data.category_slug)
        if category is None:
            raise ValueError(f"Category not found: {data.category_slug}")

        # Create skill
        skill = await self._skills.create(
            slug=data.slug,
            name=data.name,
            description=data.description,
            content=data.content,
            category_id=category.id,
            tags=data.tags,
            version=data.version,
            author_id=author_id,
            scope=data.scope.value if hasattr(data.scope, 'value') else data.scope,
            cost_profile=data.cost_profile.value if hasattr(data.cost_profile, 'value') else data.cost_profile,
            cost_drivers=data.cost_drivers,
            estimated_duration=data.estimated_duration.value if hasattr(data.estimated_duration, 'value') else str(data.estimated_duration),
            dependencies=data.dependencies.model_dump() if hasattr(data.dependencies, 'model_dump') else data.dependencies,
            eval_spec=data.eval_spec.model_dump() if hasattr(data.eval_spec, 'model_dump') else data.eval_spec,
            extends=data.extends,
            embedding=embedding,
        )

        # Create initial version record
        await self._skills.create_version(
            skill_id=skill.id,
            version=data.version,
            content=data.content,
            dependencies=data.dependencies.model_dump() if hasattr(data.dependencies, 'model_dump') else data.dependencies,
            eval_spec=data.eval_spec.model_dump() if hasattr(data.eval_spec, 'model_dump') else data.eval_spec,
            author_id=author_id,
            cost_profile=data.cost_profile.value if hasattr(data.cost_profile, 'value') else data.cost_profile,
            cost_drivers=data.cost_drivers,
            estimated_duration=data.estimated_duration.value if hasattr(data.estimated_duration, 'value') else str(data.estimated_duration),
            extends=data.extends,
            changelog="Initial version",
        )

        return skill

    async def get_skill(
        self, slug: str, version: str | None = None
    ) -> Skill | None:
        return await self._skills.get_by_slug(slug, version=version)

    async def list_skills(
        self,
        category_id: uuid_mod.UUID | None = None,
        trust_tier: str | None = None,
    ) -> list[SkillSummary]:
        return await self._skills.list_all(
            category_id=category_id, trust_tier=trust_tier
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_registry_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/services/registry.py tests/integration/test_registry_service.py
git commit -m "feat: add RegistryService with CRUD and structural validation"
```

---

### Task 14: DiscoveryService

**Files:**
- Create: `src/loom/services/discovery.py`
- Test: `tests/unit/test_discovery_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_discovery_service.py`:

```python
import uuid
from unittest.mock import AsyncMock

import pytest

from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import ResolutionContext
from loom.models.skill import Skill
from loom.services.discovery import DiscoveryService


def _skill(
    slug: str,
    trust: TrustTier = TrustTier.COMMUNITY,
    cost: CostProfile = CostProfile.FREE,
    deps: dict | None = None,
) -> Skill:
    return Skill(
        id=uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Skill {slug}",
        content=f"# {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=trust,
        cost_profile=cost,
        cost_drivers=[],
        estimated_duration="fast",
        dependencies=deps or {
            "mcp_servers": [{"uri": "filesystem", "required": True, "scopes": ["read"]}],
            "apis": [],
            "trust_requirements": {},
        },
        eval_spec={},
    )


@pytest.mark.asyncio
async def test_resolve_returns_best_match():
    """Resolve should return the best matching skill."""
    mock_repo = AsyncMock()
    mock_embedder = AsyncMock()

    candidates = [_skill("best-match"), _skill("second")]
    mock_repo.vector_search.return_value = candidates
    mock_embedder.embed_query.return_value = AsyncMock(embeddings=[[0.1] * 1536])

    svc = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    result = await svc.resolve("do the thing")
    assert result.skill.slug == "best-match"
    assert len(result.selection_rationale) > 0


@pytest.mark.asyncio
async def test_resolve_filters_by_trust_floor():
    """Skills below trust floor should be rejected."""
    mock_repo = AsyncMock()
    mock_embedder = AsyncMock()

    candidates = [
        _skill("experimental-one", trust=TrustTier.EXPERIMENTAL),
        _skill("community-one", trust=TrustTier.COMMUNITY),
    ]
    mock_repo.vector_search.return_value = candidates
    mock_embedder.embed_query.return_value = AsyncMock(embeddings=[[0.1] * 1536])

    svc = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    ctx = ResolutionContext(trust_floor=TrustTier.COMMUNITY)
    result = await svc.resolve("do the thing", context=ctx)

    assert result.skill.slug == "community-one"
    assert len(result.rejected_candidates) == 1
    assert "trust" in result.rejected_candidates[0].reason.lower()


@pytest.mark.asyncio
async def test_resolve_penalises_cost():
    """Skills over budget should be ranked lower, not eliminated."""
    mock_repo = AsyncMock()
    mock_embedder = AsyncMock()

    candidates = [
        _skill("expensive", cost=CostProfile.HIGH),
        _skill("cheap", cost=CostProfile.FREE),
    ]
    mock_repo.vector_search.return_value = candidates
    mock_embedder.embed_query.return_value = AsyncMock(embeddings=[[0.1] * 1536])

    svc = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    ctx = ResolutionContext(cost_budget=CostProfile.LOW)
    result = await svc.resolve("do the thing", context=ctx)

    assert result.skill.slug == "cheap"


@pytest.mark.asyncio
async def test_resolve_no_match():
    """Should return ResolutionError when no skills found."""
    mock_repo = AsyncMock()
    mock_embedder = AsyncMock()
    mock_repo.vector_search.return_value = []
    mock_embedder.embed_query.return_value = AsyncMock(embeddings=[[0.1] * 1536])

    svc = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    result = await svc.resolve("quantum flux calibration")

    # Should raise or return error
    from loom.models.resolution import ResolutionError
    assert isinstance(result, ResolutionError)
    assert result.error == "no_match"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_discovery_service.py -v`
Expected: FAIL

- [ ] **Step 3: Implement discovery service**

Create `src/loom/services/discovery.py`:

```python
"""Discovery service — semantic search, constraint ranking, resolution."""

from functools import lru_cache

from pydantic_ai import Embedder

from loom.db.repositories.skill_repo import SkillRepo
from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import (
    Alternative,
    RejectedCandidate,
    ResolutionContext,
    ResolutionError,
    ResolvedSkill,
)
from loom.models.skill import Skill, SkillSummary


class DiscoveryService:
    def __init__(self, skill_repo: SkillRepo, embedder: Embedder) -> None:
        self._skills = skill_repo
        self._embedder = embedder

    async def resolve(
        self,
        task_description: str,
        context: ResolutionContext | None = None,
    ) -> ResolvedSkill | ResolutionError:
        # Step 1: Generate query embedding
        embed_result = await self._embedder.embed_query(task_description)
        query_embedding = embed_result.embeddings[0]

        # Step 2: Vector search
        candidates = await self._skills.vector_search(
            query_embedding, limit=10
        )

        if not candidates:
            return ResolutionError(
                error="no_match",
                message=f"No skills matched '{task_description}' above the confidence threshold",
                suggestions=["Try broader terms", "Check available categories"],
            )

        # Step 3: Constraint filtering and ranking
        ranked, rejected = self._rank_candidates(candidates, context)

        if not ranked:
            # All candidates were filtered out
            summaries = [self._to_summary(s) for s in candidates]
            return ResolutionError(
                error="trust_floor_not_met",
                message=f"Found {len(candidates)} matching skills but none meet constraints",
                available_at_lower_tier=summaries,
            )

        best = ranked[0]
        alternatives = [
            Alternative(
                skill=self._to_summary(s),
                match_score=round(score, 3),
                tradeoff=self._describe_tradeoff(s, best),
            )
            for s, score in ranked[1:4]
        ]
        rejected_out = [
            RejectedCandidate(skill=self._to_summary(s), reason=reason)
            for s, reason in rejected
        ]

        # Step 4: Dependency status
        deps_satisfied, deps_missing = self._check_dependencies(best, context)

        # Step 5: Selection rationale
        rationale = self._explain_selection(best, ranked, rejected, context)

        return ResolvedSkill(
            skill=best,
            dependencies_satisfied=deps_satisfied,
            dependencies_missing=deps_missing,
            alternatives=alternatives,
            rejected_candidates=rejected_out,
            selection_rationale=rationale,
        )

    async def search(
        self,
        query: str,
        category_id: str | None = None,
        trust_tier: str | None = None,
        cost_budget: str | None = None,
    ) -> list[SkillSummary]:
        """Browse/filter skills — returns summaries, not full content."""
        embed_result = await self._embedder.embed_query(query)
        query_embedding = embed_result.embeddings[0]

        candidates = await self._skills.vector_search(
            query_embedding,
            limit=20,
            trust_tier=trust_tier,
        )
        return [self._to_summary(s) for s in candidates]

    def _rank_candidates(
        self,
        candidates: list[Skill],
        context: ResolutionContext | None,
    ) -> tuple[list[tuple[Skill, float]], list[tuple[Skill, str]]]:
        """Apply constraints: hard filters reject, soft scores re-rank."""
        if not context:
            return [(s, float(i)) for i, s in enumerate(candidates)], []

        scored: list[tuple[Skill, float]] = []
        rejected: list[tuple[Skill, str]] = []

        for i, skill in enumerate(candidates):
            # Hard filter: trust floor
            if context.trust_floor:
                skill_tier = TrustTier(skill.trust_tier)
                if not skill_tier.meets_floor(context.trust_floor):
                    rejected.append((
                        skill,
                        f"Below trust floor: {skill.trust_tier} < {context.trust_floor.value}",
                    ))
                    continue

            # Soft scoring: start with position score (lower = better)
            score = float(i)

            # Dependency satisfaction bonus
            if context.available_tools:
                dep_score = self._dependency_satisfaction(skill, context.available_tools)
                score *= (0.5 + 0.5 * (1.0 - dep_score))

            # Cost penalty
            if context.cost_budget:
                skill_cost = CostProfile(skill.cost_profile)
                if not skill_cost.within_budget(context.cost_budget):
                    score *= 1.5

            scored.append((skill, score))

        scored.sort(key=lambda x: x[1])
        return scored, rejected

    def _dependency_satisfaction(
        self, skill: Skill, available_tools: list[str]
    ) -> float:
        """Score 0-1 for how well available tools satisfy skill dependencies."""
        deps = skill.dependencies
        if not deps:
            return 1.0

        mcp_servers = deps.get("mcp_servers", [])
        if not mcp_servers:
            return 1.0

        required = [s for s in mcp_servers if s.get("required", True)]
        if not required:
            return 1.0

        satisfied = sum(
            1 for s in required if s.get("uri", "") in available_tools
        )
        return satisfied / len(required)

    def _check_dependencies(
        self, skill: Skill, context: ResolutionContext | None
    ) -> tuple[list[str], list[str]]:
        """Return (satisfied, missing) dependency lists."""
        available = context.available_tools if context else []
        deps = skill.dependencies
        if not deps:
            return [], []

        satisfied = []
        missing = []
        for server in deps.get("mcp_servers", []):
            uri = server.get("uri", "")
            if uri in available:
                satisfied.append(uri)
            elif server.get("required", True):
                missing.append(uri)

        return satisfied, missing

    def _explain_selection(
        self,
        best: Skill,
        ranked: list[tuple[Skill, float]],
        rejected: list[tuple[Skill, str]],
        context: ResolutionContext | None,
    ) -> list[str]:
        """Generate deterministic selection rationale."""
        rationale = [f"Best semantic match: '{best.name}'"]

        if context and context.trust_floor:
            rationale.append(
                f"Meets trust floor: {best.trust_tier} >= {context.trust_floor.value}"
            )

        if context and context.cost_budget:
            rationale.append(
                f"Within cost budget: {best.cost_profile} <= {context.cost_budget.value}"
            )

        if context and context.available_tools:
            sat, miss = self._check_dependencies(best, context)
            if miss:
                rationale.append(f"Missing optional dependencies: {', '.join(miss)}")
            else:
                rationale.append("All required dependencies satisfied")

        if len(ranked) > 1:
            rationale.append(
                f"Preferred over {len(ranked) - 1} alternative(s)"
            )

        if rejected:
            rationale.append(
                f"Excluded {len(rejected)} candidate(s) that didn't meet constraints"
            )

        return rationale

    def _describe_tradeoff(self, alternative: Skill, best: Skill) -> str:
        """Describe why the alternative wasn't chosen."""
        parts = []
        if alternative.cost_profile != best.cost_profile:
            parts.append(f"cost: {alternative.cost_profile} vs {best.cost_profile}")
        if alternative.trust_tier != best.trust_tier:
            parts.append(f"trust: {alternative.trust_tier} vs {best.trust_tier}")
        if alternative.estimated_duration != best.estimated_duration:
            parts.append(f"speed: {alternative.estimated_duration} vs {best.estimated_duration}")
        return "; ".join(parts) if parts else "Similar profile, lower semantic match"

    def _to_summary(self, skill: Skill) -> SkillSummary:
        return SkillSummary(
            id=skill.id,
            slug=skill.slug,
            name=skill.name,
            description=skill.description,
            category_id=skill.category_id,
            tags=skill.tags,
            version=skill.version,
            trust_tier=skill.trust_tier,
            cost_profile=skill.cost_profile,
            estimated_duration=skill.estimated_duration,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_discovery_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/services/discovery.py tests/unit/test_discovery_service.py
git commit -m "feat: add DiscoveryService with constraint-aware ranking"
```

---

## Chunk 5: API & MCP Entry Points

### Task 15: FastAPI Application

**Files:**
- Create: `src/loom/api/__init__.py`
- Create: `src/loom/api/app.py`
- Create: `src/loom/api/deps.py`
- Create: `src/loom/api/middleware.py`
- Create: `src/loom/api/routes/__init__.py`
- Create: `src/loom/api/routes/health.py`
- Create: `src/loom/api/routes/skills.py`
- Create: `src/loom/api/routes/categories.py`
- Create: `src/loom/api/__main__.py`
- Test: `tests/integration/test_api_health.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_api_health.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from loom.api.app import create_app


@pytest.mark.asyncio
async def test_health_endpoint():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_api_health.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the FastAPI app**

Create `src/loom/api/__init__.py` (empty).
Create `src/loom/api/routes/__init__.py` (empty).

Create `src/loom/api/routes/health.py`:

```python
"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}
```

Create `src/loom/api/middleware.py`:

```python
"""API key authentication middleware."""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """Verify the API key. Returns the key if valid.

    For M1, this is a simple check. In production, hash and compare against DB.
    """
    if api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    # TODO: M2 — look up hashed key in users table
    return api_key
```

Create `src/loom/api/deps.py`:

```python
"""FastAPI dependency injection wiring."""

from collections.abc import AsyncIterator

import asyncpg
from fastapi import Depends, Request

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.services.discovery import DiscoveryService
from loom.services.eval import EvalService
from loom.services.registry import RegistryService


async def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


async def get_conn(pool: asyncpg.Pool = Depends(get_pool)) -> AsyncIterator[asyncpg.Connection]:
    async with pool.acquire() as conn:
        yield conn


def get_skill_repo(conn: asyncpg.Connection = Depends(get_conn)) -> SkillRepo:
    return SkillRepo(conn)


def get_category_repo(conn: asyncpg.Connection = Depends(get_conn)) -> CategoryRepo:
    return CategoryRepo(conn)


def get_eval_service() -> EvalService:
    return EvalService()


def get_registry_service(
    skill_repo: SkillRepo = Depends(get_skill_repo),
    category_repo: CategoryRepo = Depends(get_category_repo),
    eval_service: EvalService = Depends(get_eval_service),
) -> RegistryService:
    return RegistryService(skill_repo, category_repo, eval_service)


def get_discovery_service(
    request: Request,
    skill_repo: SkillRepo = Depends(get_skill_repo),
) -> DiscoveryService:
    return DiscoveryService(skill_repo, request.app.state.embedder)
```

Create `src/loom/api/app.py`:

```python
"""FastAPI application factory."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from loom.api.routes import health
from loom.db.engine import create_pool
from loom.providers.embeddings import create_embedder
from loom.settings import LoomSettings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: create pool and providers. Shutdown: close pool."""
    settings = LoomSettings()

    # Database pool
    app.state.pool = await create_pool(settings.database.url)

    # Embedding provider
    app.state.embedder = create_embedder(settings.embedding)

    yield

    # Cleanup
    await app.state.pool.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Loom",
        description="Capability resolution service for agents",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health.router)

    return app
```

Create `src/loom/api/__main__.py`:

```python
"""Entry point: uv run python -m loom.api"""

import uvicorn

from loom.settings import LoomSettings

settings = LoomSettings()
uvicorn.run(
    "loom.api.app:create_app",
    factory=True,
    host=settings.api.host,
    port=settings.api.port,
    reload=True,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_api_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/api/ tests/integration/test_api_health.py
git commit -m "feat: add FastAPI app with health endpoint and DI wiring"
```

---

### Task 16: Skill & Category API Routes

**Files:**
- Create: `src/loom/api/routes/skills.py`
- Create: `src/loom/api/routes/categories.py`
- Modify: `src/loom/api/app.py` (register routers)
- Test: `tests/integration/test_api_skills.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_api_skills.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from loom.api.app import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": "test-key"},
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_list_categories(client):
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_skills(client):
    response = await client.get("/api/v1/skills")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_api_skills.py -v`
Expected: FAIL — routes don't exist

- [ ] **Step 3: Implement category routes**

Create `src/loom/api/routes/categories.py`:

```python
"""Category API routes."""

from fastapi import APIRouter, Depends

from loom.api.deps import get_category_repo
from loom.api.middleware import verify_api_key
from loom.db.repositories.category_repo import CategoryRepo
from loom.models.category import Category

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=list[Category])
async def list_categories(
    _api_key: str = Depends(verify_api_key),
    repo: CategoryRepo = Depends(get_category_repo),
):
    return await repo.list_all()
```

- [ ] **Step 4: Implement skill routes**

Create `src/loom/api/routes/skills.py`:

```python
"""Skill API routes."""

from fastapi import APIRouter, Depends, HTTPException

from loom.api.deps import get_discovery_service, get_registry_service
from loom.api.middleware import verify_api_key
from loom.models.resolution import ResolutionContext, ResolutionError, ResolvedSkill
from loom.models.skill import Skill, SkillSummary
from loom.services.discovery import DiscoveryService
from loom.services.registry import RegistryService

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


@router.get("", response_model=list[SkillSummary])
async def list_skills(
    category: str | None = None,
    trust_tier: str | None = None,
    _api_key: str = Depends(verify_api_key),
    registry: RegistryService = Depends(get_registry_service),
):
    return await registry.list_skills(trust_tier=trust_tier)


@router.get("/{slug}", response_model=Skill)
async def get_skill(
    slug: str,
    version: str | None = None,
    _api_key: str = Depends(verify_api_key),
    registry: RegistryService = Depends(get_registry_service),
):
    skill = await registry.get_skill(slug, version=version)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill not found: {slug}")
    return skill


@router.post("/resolve", response_model=ResolvedSkill)
async def resolve_skill(
    task_description: str,
    context: ResolutionContext | None = None,
    _api_key: str = Depends(verify_api_key),
    discovery: DiscoveryService = Depends(get_discovery_service),
):
    result = await discovery.resolve(task_description, context=context)
    if isinstance(result, ResolutionError):
        raise HTTPException(status_code=404, detail=result.model_dump())
    return result


@router.get("/search", response_model=list[SkillSummary])
async def search_skills(
    query: str,
    category: str | None = None,
    trust_tier: str | None = None,
    cost_budget: str | None = None,
    _api_key: str = Depends(verify_api_key),
    discovery: DiscoveryService = Depends(get_discovery_service),
):
    return await discovery.search(
        query, trust_tier=trust_tier, cost_budget=cost_budget
    )
```

- [ ] **Step 5: Register routers in app.py**

Add to `create_app()` in `src/loom/api/app.py`:

```python
from loom.api.routes import health, skills, categories

# in create_app():
app.include_router(health.router)
app.include_router(skills.router)
app.include_router(categories.router)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_api_skills.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/loom/api/routes/ src/loom/api/app.py tests/integration/test_api_skills.py
git commit -m "feat: add skill and category API routes"
```

---

### Task 17: MCP Server

**Files:**
- Create: `src/loom/mcp/__init__.py`
- Create: `src/loom/mcp/server.py`
- Create: `src/loom/mcp/tools.py`
- Test: `tests/integration/test_mcp_tools.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_mcp_tools.py`:

```python
from loom.mcp.tools import build_tools


def test_tools_are_defined():
    """MCP tools module should export the expected tool functions."""
    tools = build_tools()
    tool_names = {t.name for t in tools}
    assert "resolve" in tool_names
    assert "get_skill" in tool_names
    assert "search" in tool_names
    assert "list_categories" in tool_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_mcp_tools.py -v`
Expected: FAIL

- [ ] **Step 3: Implement MCP tools**

Create `src/loom/mcp/__init__.py` (empty).
Create `src/loom/mcp/tools.py`:

```python
"""MCP tool definitions — thin wrappers over services."""

from dataclasses import dataclass


@dataclass
class ToolDef:
    name: str
    description: str
    handler: str  # Reference to handler function name


def build_tools() -> list[ToolDef]:
    """Return the list of MCP tools Loom exposes."""
    return [
        ToolDef(
            name="resolve",
            description="Resolve the best skill for a task description, given optional runtime constraints.",
            handler="handle_resolve",
        ),
        ToolDef(
            name="get_skill",
            description="Fetch a specific skill by slug, with optional version pinning.",
            handler="handle_get_skill",
        ),
        ToolDef(
            name="search",
            description="Search skills by query with optional filters (category, trust tier, cost budget).",
            handler="handle_search",
        ),
        ToolDef(
            name="list_categories",
            description="List the category taxonomy for browsing.",
            handler="handle_list_categories",
        ),
    ]
```

Create `src/loom/mcp/server.py`:

```python
"""MCP server entry point — stdio and SSE transports."""

import asyncio

from mcp.server.fastmcp import FastMCP

from loom.db.engine import create_pool
from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.providers.embeddings import create_embedder
from loom.services.discovery import DiscoveryService
from loom.services.eval import EvalService
from loom.services.registry import RegistryService
from loom.settings import LoomSettings

mcp = FastMCP(
    name="Loom",
    instructions="Loom is a capability resolution service for agents. "
    "Use 'resolve' to find the best skill for a task. "
    "Use 'search' to browse available skills. "
    "Use 'get_skill' to fetch a specific skill by slug.",
)

# Services are initialized lazily on first tool call
_services: dict = {}  # type: ignore[type-arg]


async def _get_services() -> dict:  # type: ignore[type-arg]
    if not _services:
        settings = LoomSettings()
        pool = await create_pool(settings.database.url)
        embedder = create_embedder(settings.embedding)
        skill_repo = SkillRepo(pool)
        category_repo = CategoryRepo(pool)
        eval_svc = EvalService()

        _services["discovery"] = DiscoveryService(skill_repo, embedder)
        _services["registry"] = RegistryService(skill_repo, category_repo, eval_svc)
        _services["categories"] = category_repo
        _services["pool"] = pool

    return _services


@mcp.tool()
async def resolve(task_description: str, context: dict | None = None) -> dict:  # type: ignore[type-arg]
    """Resolve the best skill for a task.

    Args:
        task_description: Natural language description of what you need to do.
        context: Optional runtime constraints — trust_floor, cost_budget,
                 available_tools, etc.
    """
    from loom.models.resolution import ResolutionContext

    svcs = await _get_services()
    ctx = ResolutionContext(**context) if context else None
    result = await svcs["discovery"].resolve(task_description, context=ctx)
    return result.model_dump()


@mcp.tool()
async def get_skill(slug: str, version: str | None = None) -> dict:  # type: ignore[type-arg]
    """Fetch a specific skill by slug. Supports version pinning for extends references.

    Args:
        slug: The skill's unique slug identifier.
        version: Optional semver version. If omitted, returns latest.
    """
    svcs = await _get_services()
    skill = await svcs["registry"].get_skill(slug, version=version)
    if skill is None:
        return {"error": "not_found", "message": f"Skill not found: {slug}"}
    return skill.model_dump()


@mcp.tool()
async def search(
    query: str,
    category: str | None = None,
    trust_tier: str | None = None,
    cost_budget: str | None = None,
) -> list[dict]:  # type: ignore[type-arg]
    """Search skills by query. Returns summaries without full content.

    Args:
        query: Natural language search query.
        category: Optional category slug filter.
        trust_tier: Minimum trust tier (experimental, community, verified).
        cost_budget: Maximum cost profile (free, low, moderate, high).
    """
    svcs = await _get_services()
    results = await svcs["discovery"].search(
        query, trust_tier=trust_tier, cost_budget=cost_budget
    )
    return [r.model_dump() for r in results]


@mcp.tool()
async def list_categories() -> list[dict]:  # type: ignore[type-arg]
    """List the category taxonomy for browsing."""
    svcs = await _get_services()
    categories = await svcs["categories"].list_all()
    return [c.model_dump() for c in categories]


def main() -> None:
    """Entry point for the MCP server."""
    settings = LoomSettings()

    # Determine transport from config
    transports = settings.mcp.transports
    stdio = any(t.type == "stdio" for t in transports)
    sse_config = next((t for t in transports if t.type == "sse"), None)

    if stdio:
        mcp.run(transport="stdio")
    elif sse_config:
        mcp.run(transport="sse", host=sse_config.host, port=sse_config.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_mcp_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/mcp/ tests/integration/test_mcp_tools.py
git commit -m "feat: add MCP server with resolve, search, get_skill, list_categories"
```

---

## Chunk 6: Seed Content & End-to-End Demo

### Task 18: Seed Skills

**Files:**
- Create: `seeds/development/git/conventional-commit.yaml`
- Create: `seeds/development/git/commit-ai-message.yaml`
- Create: `seeds/development/git/commit-github-enriched.yaml`
- Create: `seeds/development/testing/write-unit-tests.yaml`
- Create: `seeds/documentation/release-notes-local.yaml`
- Create: `seeds/documentation/release-notes-enriched.yaml`
- Create: `seeds/code-review/review-pull-request.yaml`
- Create: `scripts/seed.py`

- [ ] **Step 1: Create seed skill files**

Create at least 7 seed skills across 4 categories. Each must have complete frontmatter including `eval_spec`, `dependencies`, `cost_profile`, and `privacy_impact`. At least 3 skills should form a "cluster" addressing the same task with different trade-offs (e.g., 3 different commit skills with varying deps/cost).

Example `seeds/development/git/conventional-commit.yaml`:

```yaml
slug: "git-commit-conventional"
name: "Conventional Commit"
description: "Create git commits following the Conventional Commits specification with automatic scope detection"
category: "development/git"
tags: ["git", "commits", "conventions"]
version: "1.0.0"
cost_profile: "free"
cost_drivers: []
estimated_duration: "fast"
extends: null

dependencies:
  mcp_servers:
    - uri: "filesystem"
      required: true
      scopes: ["read"]
    - uri: "git"
      required: true
      scopes: ["read", "write"]
  apis: []
  trust_requirements:
    data_classification: "none"
    network_access: false
    privacy_impact:
      external_data_sharing: false
      input_logging: "none"
      data_retention: "none"

eval_spec:
  scenarios:
    - description: "Agent needs to commit staged changes"
      input_context: "Modified files in git repo, changes staged"
      success_criteria: "Produces a valid conventional commit message with appropriate type and scope"
    - description: "Agent encounters merge conflict"
      input_context: "Git repo with unresolved conflicts"
      success_criteria: "Skill correctly identifies this as out-of-scope or handles gracefully"
  quality_dimensions:
    - name: "clarity"
      description: "Instructions are unambiguous and followable"
    - name: "completeness"
      description: "All common edge cases addressed"
    - name: "minimalism"
      description: "No unnecessary steps"

content: |
  # Conventional Commit

  When creating git commits, follow the Conventional Commits specification.

  ## Steps

  1. Review staged changes with `git diff --staged`
  2. Identify the change type: feat, fix, docs, style, refactor, test, chore
  3. Identify the scope from the most-changed directory
  4. Write the commit message: `<type>(<scope>): <description>`
  5. Description should be imperative mood, lowercase, no period
  6. If the change is breaking, add `BREAKING CHANGE:` in the footer

  ## Examples

  - `feat(auth): add OAuth2 login flow`
  - `fix(api): handle null response from upstream`
  - `docs(readme): update installation instructions`
```

Create similar files for the other seeds. The key cluster for demo purposes is three "release notes" or "commit" skills with different dependency/cost profiles.

- [ ] **Step 2: Create the seed loading script**

Create `scripts/seed.py`:

```python
"""Load seed skills into the database."""

import asyncio
import os
from pathlib import Path

import yaml

from loom.db.engine import create_pool
from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.category import CategoryCreate
from loom.providers.embeddings import create_embedder
from loom.services.eval import EvalService
from loom.services.registry import RegistryService
from loom.models.skill import SkillCreate
from loom.models.common import EvalSpec, DependencyDeclaration
from loom.settings import LoomSettings


async def main() -> None:
    settings = LoomSettings()
    pool = await create_pool(settings.database.url)
    embedder = create_embedder(settings.embedding)

    async with pool.acquire() as conn:
        cat_repo = CategoryRepo(conn)
        skill_repo = SkillRepo(conn)
        eval_svc = EvalService()
        registry = RegistryService(skill_repo, cat_repo, eval_svc)

        # Ensure a seed user exists
        user = await conn.fetchrow("SELECT id FROM users WHERE handle = 'loom-seed'")
        if not user:
            user = await conn.fetchrow(
                """
                INSERT INTO users (handle, email, api_key, role)
                VALUES ('loom-seed', 'seed@loom.dev', 'seed-api-key', 'maintainer')
                RETURNING id
                """
            )
        user_id = user["id"]

        # Load all seed YAML files
        seeds_dir = Path("seeds")
        for yaml_path in sorted(seeds_dir.rglob("*.yaml")):
            with open(yaml_path) as f:
                data = yaml.safe_load(f)

            slug = data["slug"]

            # Check if already exists
            existing = await skill_repo.get_by_slug(slug)
            if existing:
                print(f"  Skipping {slug} (already exists)")
                continue

            # Ensure category exists
            cat_slug = data["category"]
            cat = await cat_repo.get_by_slug(cat_slug)
            if not cat:
                # Create category hierarchy
                parts = cat_slug.split("/")
                for i in range(len(parts)):
                    partial = "/".join(parts[: i + 1])
                    existing_cat = await cat_repo.get_by_slug(partial)
                    if not existing_cat:
                        parent_slug = "/".join(parts[:i]) if i > 0 else None
                        parent = await cat_repo.get_by_slug(parent_slug) if parent_slug else None
                        await cat_repo.create(CategoryCreate(
                            slug=partial,
                            name=parts[i].title(),
                            parent_id=parent.id if parent else None,
                        ))
                cat = await cat_repo.get_by_slug(cat_slug)

            # Generate embedding
            print(f"  Embedding {slug}...")
            embed_text = f"{data['name']}: {data['description']}\n{data['content']}"
            embed_result = await embedder.embed_query(embed_text)
            embedding = embed_result.embeddings[0]

            # Create skill
            await registry.create_skill(
                data=SkillCreate(
                    slug=slug,
                    name=data["name"],
                    description=data["description"],
                    content=data["content"],
                    category_slug=cat_slug,
                    version=data.get("version", "1.0.0"),
                    tags=data.get("tags", []),
                    cost_profile=data.get("cost_profile", "free"),
                    cost_drivers=data.get("cost_drivers", []),
                    estimated_duration=data.get("estimated_duration", "fast"),
                    extends=data.get("extends"),
                    eval_spec=EvalSpec(**data["eval_spec"]) if "eval_spec" in data else EvalSpec(),
                    dependencies=DependencyDeclaration(**data["dependencies"]) if "dependencies" in data else DependencyDeclaration(),
                ),
                author_id=user_id,
                embedding=embedding,
            )
            print(f"  Created {slug}")

    await pool.close()
    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Write remaining seed skill YAML files**

Create at least 6 more seed files covering the required clusters. Key cluster: 3 skills for "summarise code changes for release notes" with different dependency/cost trade-offs:

1. `seeds/documentation/release-notes-local.yaml` — free, requires only `git`, fast
2. `seeds/documentation/release-notes-enriched.yaml` — low cost, requires `git` + `web-search`, moderate
3. `seeds/documentation/release-notes-ai.yaml` — moderate cost, requires LLM API, slow but higher quality

Plus at least 2 skills with `extends` references.

- [ ] **Step 4: Run the seed script**

Run: `OPENAI_API_KEY=your-key uv run python scripts/seed.py`
Expected: All seeds loaded, embeddings generated.

- [ ] **Step 5: Commit**

```bash
git add seeds/ scripts/seed.py
git commit -m "feat: add seed skills and loading script"
```

---

### Task 19: End-to-End Smoke Test

**Files:**
- Create: `tests/integration/test_e2e_resolve.py`

- [ ] **Step 1: Write the end-to-end test**

This test requires seeds to be loaded and a real embedding API. Mark it as a separate test group.

Create `tests/integration/test_e2e_resolve.py`:

```python
"""End-to-end resolution test — requires running DB with seeds and OPENAI_API_KEY."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY required for e2e tests",
)


@pytest.mark.asyncio
async def test_resolve_different_contexts():
    """The same task should resolve differently under different constraints.

    This is the M1 demo: prove constraint-aware resolution works.
    """
    from loom.db.engine import create_pool
    from loom.db.repositories.skill_repo import SkillRepo
    from loom.models.resolution import ResolutionContext, ResolutionError
    from loom.models.common import CostProfile
    from loom.providers.embeddings import create_embedder
    from loom.services.discovery import DiscoveryService
    from loom.settings import LoomSettings

    settings = LoomSettings()
    pool = await create_pool(settings.database.url)

    try:
        async with pool.acquire() as conn:
            embedder = create_embedder(settings.embedding)
            skill_repo = SkillRepo(conn)
            discovery = DiscoveryService(skill_repo, embedder)

            # Low budget, minimal tools
            result_low = await discovery.resolve(
                "summarise recent code changes for release notes",
                context=ResolutionContext(
                    cost_budget=CostProfile.FREE,
                    available_tools=["git", "filesystem"],
                ),
            )

            # Higher budget, more tools
            result_high = await discovery.resolve(
                "summarise recent code changes for release notes",
                context=ResolutionContext(
                    cost_budget=CostProfile.HIGH,
                    available_tools=["git", "filesystem", "web-search"],
                ),
            )

            # Both should succeed
            assert not isinstance(result_low, ResolutionError), f"Low budget failed: {result_low}"
            assert not isinstance(result_high, ResolutionError), f"High budget failed: {result_high}"

            # They should resolve different skills (or at least different rankings)
            # The exact assertion depends on seed data, but at minimum:
            assert result_low.skill is not None
            assert result_high.skill is not None
            assert len(result_low.selection_rationale) > 0
            print(f"Low budget: {result_low.skill.slug}")
            print(f"High budget: {result_high.skill.slug}")
    finally:
        await pool.close()
```

- [ ] **Step 2: Run the e2e test**

Run: `OPENAI_API_KEY=your-key uv run pytest tests/integration/test_e2e_resolve.py -v -s`
Expected: PASS — different skills resolved under different constraints.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_e2e_resolve.py
git commit -m "feat: add end-to-end resolution test proving constraint-aware ranking"
```

---

## Chunk 7: Missing Deliverables

### Task 20: Skill Update (Version Bump)

**Files:**
- Modify: `src/loom/db/repositories/skill_repo.py`
- Modify: `src/loom/services/registry.py`
- Modify: `src/loom/api/routes/skills.py`
- Create: `src/loom/models/skill.py` (add `SkillUpdate`)
- Test: `tests/integration/test_skill_update.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_skill_update.py`:

```python
import asyncpg
import pytest

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.category import CategoryCreate
from loom.models.common import EvalScenario, EvalSpec, QualityDimension
from loom.models.skill import SkillCreate, SkillUpdate
from loom.services.eval import EvalService
from loom.services.registry import RegistryService


@pytest.fixture
async def registry_with_skill(db_conn: asyncpg.Connection):
    """Create a registry with a category, user, and initial skill."""
    cat_repo = CategoryRepo(db_conn)
    skill_repo = SkillRepo(db_conn)
    eval_svc = EvalService()
    svc = RegistryService(skill_repo, cat_repo, eval_svc)

    await cat_repo.create(CategoryCreate(slug="dev/git", name="Git"))
    user = await db_conn.fetchrow(
        "INSERT INTO users (handle, email, api_key) VALUES ('u', 'u@e.com', 'k') RETURNING id"
    )
    user_id = user["id"]

    skill = await svc.create_skill(
        data=SkillCreate(
            slug="updatable-skill",
            name="Updatable",
            description="A skill to update",
            content="# V1\nOriginal content with enough length.",
            category_slug="dev/git",
            version="1.0.0",
            eval_spec=EvalSpec(
                scenarios=[EvalScenario(description="X", input_context="Y", success_criteria="Z")],
                quality_dimensions=[QualityDimension(name="c", description="d")],
            ),
        ),
        author_id=user_id,
    )
    return svc, skill, user_id


@pytest.mark.asyncio
async def test_update_skill_bumps_version(registry_with_skill):
    svc, original, user_id = registry_with_skill
    updated = await svc.update_skill(
        slug="updatable-skill",
        data=SkillUpdate(
            content="# V2\nUpdated content with enough length for validation.",
            version="1.1.0",
            changelog="Improved instructions",
        ),
        author_id=user_id,
    )
    assert updated.version == "1.1.0"
    assert "V2" in updated.content
    assert updated.id == original.id  # Same skill, new version


@pytest.mark.asyncio
async def test_update_creates_version_record(registry_with_skill):
    svc, original, user_id = registry_with_skill
    await svc.update_skill(
        slug="updatable-skill",
        data=SkillUpdate(
            content="# V2\nUpdated content with enough length for validation.",
            version="1.1.0",
            changelog="Improved",
        ),
        author_id=user_id,
    )
    # Old version should still be retrievable
    old = await svc.get_skill("updatable-skill", version="1.0.0")
    assert old is not None
    assert "V1" in old.content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_skill_update.py -v`
Expected: FAIL — `SkillUpdate` and `update_skill` don't exist

- [ ] **Step 3: Add SkillUpdate model**

Add to `src/loom/models/skill.py`:

```python
class SkillUpdate(BaseModel):
    """Input model for updating a skill (version bump)."""

    content: str | None = None
    description: str | None = None
    version: str  # required — must be a new version
    tags: list[str] | None = None
    cost_profile: CostProfile | None = None
    cost_drivers: list[str] | None = None
    estimated_duration: EstimatedDuration | str | None = None
    dependencies: DependencyDeclaration | None = None
    eval_spec: EvalSpec | None = None
    extends: str | None = None
    changelog: str | None = None
```

- [ ] **Step 4: Add update method to SkillRepo**

Add to `src/loom/db/repositories/skill_repo.py`:

```python
    async def update(
        self,
        skill_id: uuid_mod.UUID,
        *,
        content: str,
        description: str,
        version: str,
        tags: list[str],
        cost_profile: str,
        cost_drivers: list[str],
        estimated_duration: str,
        dependencies: dict,  # type: ignore[type-arg]
        eval_spec: dict,  # type: ignore[type-arg]
        extends: str | None,
    ) -> Skill:
        row = await self._conn.fetchrow(
            """
            UPDATE skills SET
                content = $2, description = $3, version = $4, tags = $5,
                cost_profile = $6, cost_drivers = $7, estimated_duration = $8,
                dependencies = $9, eval_spec = $10, extends = $11,
                updated_at = now()
            WHERE id = $1
            RETURNING *
            """,
            skill_id, content, description, version, tags,
            cost_profile, cost_drivers, estimated_duration,
            dependencies, eval_spec, extends,
        )
        return self._row_to_skill(row)
```

- [ ] **Step 5: Add update_skill to RegistryService**

Add to `src/loom/services/registry.py`:

```python
    async def update_skill(
        self,
        slug: str,
        data: "SkillUpdate",
        author_id: uuid_mod.UUID,
        embedding: list[float] | None = None,
    ) -> Skill:
        from loom.models.skill import SkillUpdate

        existing = await self._skills.get_by_slug(slug)
        if existing is None:
            raise ValueError(f"Skill not found: {slug}")

        # Merge: use new values where provided, keep existing otherwise
        content = data.content or existing.content
        description = data.description or existing.description
        deps = data.dependencies.model_dump() if data.dependencies else existing.dependencies
        eval_sp = data.eval_spec.model_dump() if data.eval_spec else existing.eval_spec

        # Validate
        result = self._eval.validate_structure(content=content, dependencies=deps, eval_spec=eval_sp)
        if not result.passed:
            raise ValueError(f"Structural validation failed: {'; '.join(result.errors)}")

        # Update skill (latest)
        updated = await self._skills.update(
            skill_id=existing.id,
            content=content,
            description=description,
            version=data.version,
            tags=data.tags if data.tags is not None else existing.tags,
            cost_profile=(data.cost_profile.value if data.cost_profile else existing.cost_profile),
            cost_drivers=data.cost_drivers if data.cost_drivers is not None else existing.cost_drivers,
            estimated_duration=(
                data.estimated_duration.value
                if data.estimated_duration and hasattr(data.estimated_duration, 'value')
                else str(data.estimated_duration or existing.estimated_duration)
            ),
            dependencies=deps,
            eval_spec=eval_sp,
            extends=data.extends if data.extends is not None else existing.extends,
        )

        # Create version record
        await self._skills.create_version(
            skill_id=existing.id,
            version=data.version,
            content=content,
            dependencies=deps,
            eval_spec=eval_sp,
            author_id=author_id,
            cost_profile=updated.cost_profile,
            cost_drivers=updated.cost_drivers,
            estimated_duration=updated.estimated_duration,
            extends=updated.extends,
            changelog=data.changelog,
        )

        return updated
```

- [ ] **Step 6: Add PUT route**

Add to `src/loom/api/routes/skills.py`:

```python
from loom.models.skill import SkillUpdate

@router.put("/{slug}", response_model=Skill)
async def update_skill(
    slug: str,
    data: SkillUpdate,
    _api_key: str = Depends(verify_api_key),
    registry: RegistryService = Depends(get_registry_service),
):
    # TODO: resolve author_id from API key
    try:
        return await registry.update_skill(slug, data, author_id=uuid.uuid4())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_skill_update.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/loom/models/skill.py src/loom/db/repositories/skill_repo.py src/loom/services/registry.py src/loom/api/routes/skills.py tests/integration/test_skill_update.py
git commit -m "feat: add skill update with version bump"
```

---

### Task 21: Reference Python `extends` Resolver

**Files:**
- Create: `src/loom/extends/__init__.py`
- Create: `src/loom/extends/resolver.py`
- Test: `tests/unit/test_extends_resolver.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_extends_resolver.py`:

```python
import pytest

from loom.extends.resolver import ExtendsResolver, ResolvedChain


def test_no_extends():
    """A skill with no extends returns just its own content."""
    resolver = ExtendsResolver()
    result = resolver.merge_layers([
        {"slug": "my-skill", "content": "# My Skill\nDo the thing."},
    ])
    assert "My Skill" in result.merged_content
    assert len(result.layers) == 1


def test_two_layer_merge():
    """Community + personal should merge with correct precedence."""
    resolver = ExtendsResolver()
    result = resolver.merge_layers([
        {"slug": "community-skill", "content": "# Community\nGeneral instructions.", "scope": "community"},
        {"slug": "personal-override", "content": "Also do my personal thing.", "scope": "personal"},
    ])
    assert "Community" in result.merged_content
    assert "personal thing" in result.merged_content
    # Personal layer should come after community
    assert result.merged_content.index("Community") < result.merged_content.index("personal thing")


def test_three_layer_merge():
    """Community + corporate + personal should merge in priority order."""
    resolver = ExtendsResolver()
    result = resolver.merge_layers([
        {"slug": "community-base", "content": "# Base\nGeneral.", "scope": "community"},
        {"slug": "corp-overlay", "content": "Use our internal API.", "scope": "corporate"},
        {"slug": "my-prefs", "content": "Route to #my-channel.", "scope": "personal"},
    ])
    assert len(result.layers) == 3
    assert "General" in result.merged_content
    assert "internal API" in result.merged_content
    assert "#my-channel" in result.merged_content


def test_parse_extends_uri():
    """Should parse loom:// and corp:// URIs with version pinning."""
    resolver = ExtendsResolver()

    source, slug, version = resolver.parse_extends_uri("loom://vendor-risk@verified")
    assert source == "loom"
    assert slug == "vendor-risk"
    assert version == "verified"

    source, slug, version = resolver.parse_extends_uri("corp://acme-tool@1.2.0")
    assert source == "corp"
    assert slug == "acme-tool"
    assert version == "1.2.0"

    source, slug, version = resolver.parse_extends_uri("loom://basic-skill")
    assert source == "loom"
    assert slug == "basic-skill"
    assert version is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_extends_resolver.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the extends resolver**

Create `src/loom/extends/__init__.py` (empty).
Create `src/loom/extends/resolver.py`:

```python
"""Reference implementation of client-side `extends` chain resolution.

This is a library for agent runtimes to merge skill layers:
  community base -> corporate refinements -> personal preferences

The merge is intentionally simple: append with delimiters, not field-level merge.
Higher-priority layers refine lower ones. Later sections override earlier ones.
"""

import re
from dataclasses import dataclass, field


@dataclass
class LayerInfo:
    slug: str
    scope: str
    content: str


@dataclass
class ResolvedChain:
    merged_content: str
    layers: list[LayerInfo]


class ExtendsResolver:
    """Merges skill layers following the extends chain.

    Usage:
        resolver = ExtendsResolver()
        # Resolve each layer (community, corporate, personal) via Loom or local
        layers = [community_skill, corporate_skill, personal_skill]
        result = resolver.merge_layers(layers)
        # result.merged_content contains the fully merged instructions
    """

    # URI pattern: source://slug@version
    _URI_PATTERN = re.compile(r"^(loom|corp)://([^@]+)(?:@(.+))?$")

    def merge_layers(self, layers: list[dict]) -> ResolvedChain:  # type: ignore[type-arg]
        """Merge skill layers in priority order (first = lowest priority).

        Each layer is a dict with at least 'slug' and 'content'.
        Optional 'scope' defaults to 'community'.

        Layers are appended in order with clear delimiters.
        The agent treats later sections as higher priority.
        """
        if not layers:
            return ResolvedChain(merged_content="", layers=[])

        layer_infos: list[LayerInfo] = []
        content_parts: list[str] = []

        scope_labels = {
            "community": "Community Base",
            "corporate": "Corporate Context",
            "personal": "Local Overrides",
        }

        for i, layer in enumerate(layers):
            slug = layer.get("slug", "unknown")
            scope = layer.get("scope", "community")
            content = layer.get("content", "")

            layer_infos.append(LayerInfo(slug=slug, scope=scope, content=content))

            if i == 0:
                content_parts.append(content)
            else:
                label = scope_labels.get(scope, scope.title())
                content_parts.append(f"\n\n---\n## {label}\n{content}")

        merged = "".join(content_parts)
        return ResolvedChain(merged_content=merged, layers=layer_infos)

    def parse_extends_uri(self, uri: str) -> tuple[str, str, str | None]:
        """Parse an extends URI into (source, slug, version).

        Examples:
            loom://vendor-risk@verified -> ("loom", "vendor-risk", "verified")
            corp://acme-tool@1.2.0 -> ("corp", "acme-tool", "1.2.0")
            loom://basic-skill -> ("loom", "basic-skill", None)
        """
        match = self._URI_PATTERN.match(uri)
        if not match:
            raise ValueError(f"Invalid extends URI: {uri}")
        source, slug, version = match.groups()
        return source, slug, version
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_extends_resolver.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/loom/extends/ tests/unit/test_extends_resolver.py
git commit -m "feat: add reference extends resolver for client-side layer merging"
```

---

### Task 22: CI (GitHub Actions)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - run: uv sync --all-extras
      - run: uv run ruff check src/ tests/
      - run: uv run ruff format --check src/ tests/
      - run: uv run mypy src/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg17
        env:
          POSTGRES_DB: loom
          POSTGRES_USER: loom
          POSTGRES_PASSWORD: loom
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U loom"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - run: uv sync --all-extras
      - run: uv run alembic upgrade head
      - run: uv run pytest tests/unit/ -v
      - run: uv run pytest tests/integration/ -v --ignore=tests/integration/test_e2e_resolve.py
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "feat: add GitHub Actions CI for linting, type checking, and tests"
```

---

### Task 23: MCP `__main__` Module

**Files:**
- Create: `src/loom/mcp/__main__.py`

- [ ] **Step 1: Create __main__.py for module consistency**

Create `src/loom/mcp/__main__.py`:

```python
"""Entry point: uv run python -m loom.mcp"""

from loom.mcp.server import main

main()
```

- [ ] **Step 2: Commit**

```bash
git add src/loom/mcp/__main__.py
git commit -m "feat: add MCP __main__ module for 'python -m loom.mcp'"
```

---

### Task 24: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README with setup and demo instructions**

The README should cover:
- What Loom is (1 paragraph)
- Prerequisites (Python 3.12, uv, Docker)
- Setup (`uv sync`, `docker compose up -d`, `uv run alembic upgrade head`, seed script)
- Running the API (`uv run python -m loom.api`)
- Running the MCP server (`uv run python -m loom.mcp` or `uv run python -m loom.mcp.server`)
- Connecting from Claude Code (MCP config snippet)
- Running tests (`uv run pytest`)

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, demo, and MCP connection instructions"
```

---

### Task 25: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: All unit and integration tests pass (e2e skipped without API key).

- [ ] **Step 2: Run linting and type checking**

Run: `uv run ruff check src/ tests/ && uv run mypy src/`
Expected: Clean.

- [ ] **Step 3: Verify MCP server starts**

Run: `uv run python -m loom.mcp.server` (should start in stdio mode, Ctrl+C to exit).

- [ ] **Step 4: Verify API server starts**

Run: `uv run python -m loom.api` (should start on port 8000, Ctrl+C to exit).

- [ ] **Step 5: Verify OpenAPI docs**

Navigate to `http://localhost:8000/docs` — should show Swagger UI with all routes.

- [ ] **Step 6: Final commit if any cleanup needed**

```bash
git add -A && git commit -m "chore: final M1 cleanup and verification"
```
