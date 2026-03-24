#!/usr/bin/env python3
"""Seed script: load skills from seeds/ directory into the Loom database.

Usage:
    uv run python scripts/seed.py

Embeddings are generated using the provider configured in loom.yaml.
API key should be set in .env (e.g. OPENROUTER_API_KEY=...).
The script is idempotent: skills that already exist (by slug) are skipped.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

import asyncpg
import yaml

# ---------------------------------------------------------------------------
# Resolve project root and add src/ to path so loom package is importable
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import json  # noqa: E402

from loom.db.repositories.capability_repo import CapabilityRepo  # noqa: E402
from loom.db.repositories.category_repo import CategoryRepo  # noqa: E402
from loom.db.repositories.skill_repo import SkillRepo  # noqa: E402
from loom.models.capability import CapabilityCreate, CapabilityStep, DataFlowEdge  # noqa: E402
from loom.models.category import CategoryCreate  # noqa: E402
from loom.models.common import (  # noqa: E402
    APIDependency,
    CostProfile,
    DependencyDeclaration,
    EstimatedDuration,
    EvalScenario,
    EvalSpec,
    MCPServerDependency,
    PrivacyImpact,
    QualityDimension,
    Scope,
    TrustRequirements,
    TrustTier,
)
from loom.models.skill import SkillCreate  # noqa: E402
from loom.providers.embeddings import create_embedder  # noqa: E402
from loom.services.eval import EvalService  # noqa: E402
from loom.services.registry import RegistryService  # noqa: E402
from loom.settings import LoomSettings  # noqa: E402

SEEDS_DIR = REPO_ROOT / "seeds"
SEED_USER_HANDLE = "loom-seed"
SEED_USER_EMAIL = "seed@loom.internal"

# ---------------------------------------------------------------------------
# Embedding helper (uses provider factory from settings)
# ---------------------------------------------------------------------------

_embedder = None


def _get_embedder(settings: LoomSettings):  # type: ignore[no-untyped-def]
    """Lazily create the embedder from settings, or return None if no API key."""
    global _embedder  # noqa: PLW0603
    if _embedder is not None:
        return _embedder
    try:
        _embedder = create_embedder(settings.embedding)
        return _embedder
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] could not create embedder: {exc}")
        return None


async def get_embedding(text: str, settings: LoomSettings) -> list[float] | None:
    """Return an embedding vector using the configured provider, or None."""
    embedder = _get_embedder(settings)
    if embedder is None:
        return None
    try:
        result = await embedder.embed_query(text)
        return list(result.embeddings[0])
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] embedding failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# YAML → Pydantic model helpers
# ---------------------------------------------------------------------------


def _parse_privacy_impact(raw: dict) -> PrivacyImpact:
    return PrivacyImpact(
        external_data_sharing=raw.get("external_data_sharing", False),
        input_logging=raw.get("input_logging", "none"),
        data_retention=raw.get("data_retention", "none"),
    )


def _parse_trust_requirements(raw: dict) -> TrustRequirements:
    pi_raw = raw.get("privacy_impact", {})
    return TrustRequirements(
        data_classification=raw.get("data_classification", "none"),
        network_access=raw.get("network_access", False),
        privacy_impact=_parse_privacy_impact(pi_raw),
    )


def _parse_dependencies(raw: dict) -> DependencyDeclaration:
    mcp_servers = [
        MCPServerDependency(
            uri=s["uri"],
            required=s.get("required", True),
            scopes=s.get("scopes", []),
        )
        for s in raw.get("mcp_servers", [])
    ]
    apis = [
        APIDependency(
            name=a["name"],
            auth_type=a.get("auth_type", "api_key"),
            scopes=a.get("scopes", []),
        )
        for a in raw.get("apis", [])
    ]
    tr_raw = raw.get("trust_requirements", {})
    return DependencyDeclaration(
        mcp_servers=mcp_servers,
        apis=apis,
        trust_requirements=_parse_trust_requirements(tr_raw),
    )


def _parse_eval_spec(raw: dict) -> EvalSpec:
    scenarios = [
        EvalScenario(
            description=s["description"],
            input_context=s["input_context"],
            success_criteria=s["success_criteria"],
        )
        for s in raw.get("scenarios", [])
    ]
    dimensions = [
        QualityDimension(name=d["name"], description=d["description"])
        for d in raw.get("quality_dimensions", [])
    ]
    return EvalSpec(scenarios=scenarios, quality_dimensions=dimensions)


def yaml_to_skill_create(data: dict) -> SkillCreate:
    """Convert a parsed YAML dict into a SkillCreate model."""
    cost_profile_raw = data.get("cost_profile", "free")
    cost_profile = CostProfile(cost_profile_raw) if cost_profile_raw else CostProfile.FREE

    duration_raw = data.get("estimated_duration", "fast")
    try:
        estimated_duration = EstimatedDuration(duration_raw)
    except ValueError:
        estimated_duration = EstimatedDuration.FAST

    return SkillCreate(
        slug=data["slug"],
        name=data["name"],
        description=data["description"],
        content=data["content"],
        category_slug=data["category"],
        version=data.get("version", "1.0.0"),
        tags=data.get("tags", []),
        scope=Scope.COMMUNITY,
        trust_tier=TrustTier.COMMUNITY,
        cost_profile=cost_profile,
        cost_drivers=data.get("cost_drivers", []),
        estimated_duration=estimated_duration,
        dependencies=_parse_dependencies(data.get("dependencies", {})),
        eval_spec=_parse_eval_spec(data.get("eval_spec", {})),
        extends=data.get("extends"),
    )


# ---------------------------------------------------------------------------
# Category hierarchy helpers
# ---------------------------------------------------------------------------


async def ensure_category_hierarchy(
    category_repo: CategoryRepo,
    category_slug: str,
) -> None:
    """Create parent and leaf categories for a slug like 'development/git'."""
    parts = category_slug.split("/")
    parent_id = None

    for i, part in enumerate(parts):
        slug = "/".join(parts[: i + 1])
        existing = await category_repo.get_by_slug(slug)
        if existing is not None:
            parent_id = existing.id
            continue

        # Build a display name from the slug part
        name = part.replace("-", " ").title()
        created = await category_repo.create(
            CategoryCreate(
                slug=slug,
                name=name,
                description=None,
                parent_id=parent_id,
            )
        )
        print(f"  [+] category: {slug!r}")
        parent_id = created.id


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------


async def ensure_seed_user(conn: asyncpg.Connection) -> uuid.UUID:
    """Return the id of the loom-seed user, creating it if necessary."""
    row = await conn.fetchrow("SELECT id FROM users WHERE handle = $1", SEED_USER_HANDLE)
    if row is not None:
        return row["id"]

    # Generate a random API key — not used for real auth
    api_key = f"seed-{uuid.uuid4().hex}"
    row = await conn.fetchrow(
        """
        INSERT INTO users (handle, email, api_key, role)
        VALUES ($1, $2, $3, 'contributor')
        RETURNING id
        """,
        SEED_USER_HANDLE,
        SEED_USER_EMAIL,
        api_key,
    )
    print(f"  [+] user: {SEED_USER_HANDLE!r} ({row['id']})")
    return row["id"]


# ---------------------------------------------------------------------------
# Main seed routine
# ---------------------------------------------------------------------------


async def _init_conn(conn: asyncpg.Connection) -> None:
    """Set up JSONB codec and pgvector for each pool connection."""
    from pgvector.asyncpg import register_vector

    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await register_vector(conn)


async def seed() -> None:
    settings = LoomSettings()
    print(f"Connecting to database: {settings.database.url!r}")

    url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=5, init=_init_conn)
    assert pool is not None

    has_embedder = _get_embedder(settings) is not None
    if has_embedder:
        print(f"Embedding provider: {settings.embedding.provider}/{settings.embedding.model}")
    else:
        print("No embedding API key found — skills will be created without embeddings.")

    yaml_files = sorted(SEEDS_DIR.rglob("*.yaml"))
    print(f"\nFound {len(yaml_files)} seed files in {SEEDS_DIR}\n")

    created = 0
    skipped = 0
    errors = 0

    async with pool.acquire() as conn:
        author_id = await ensure_seed_user(conn)

        skill_repo = SkillRepo(conn)
        category_repo = CategoryRepo(conn)
        eval_service = EvalService()
        registry = RegistryService(skill_repo, category_repo, eval_service)

        for yaml_path in yaml_files:
            relative = yaml_path.relative_to(REPO_ROOT)
            print(f"Processing {relative} …")

            try:
                raw = yaml.safe_load(yaml_path.read_text())
            except yaml.YAMLError as exc:
                print(f"  [error] YAML parse failed: {exc}")
                errors += 1
                continue

            slug = raw.get("slug", "")
            if not slug:
                print("  [error] missing 'slug' field — skipped")
                errors += 1
                continue

            # Idempotency check
            existing = await skill_repo.get_by_slug(slug)
            if existing is not None:
                print(f"  [skip] slug {slug!r} already exists")
                skipped += 1
                continue

            # Ensure categories exist
            category_slug = raw.get("category", "")
            if not category_slug:
                print("  [error] missing 'category' field — skipped")
                errors += 1
                continue

            try:
                await ensure_category_hierarchy(category_repo, category_slug)
            except Exception as exc:  # noqa: BLE001
                print(f"  [error] category creation failed: {exc}")
                errors += 1
                continue

            # Parse skill
            try:
                skill_create = yaml_to_skill_create(raw)
            except Exception as exc:  # noqa: BLE001
                print(f"  [error] model parse failed: {exc}")
                errors += 1
                continue

            # Generate embedding
            embedding = None
            if has_embedder:
                embed_text = (
                    f"{skill_create.name}\n{skill_create.description}\n{skill_create.content}"
                )
                embedding = await get_embedding(embed_text, settings)
                if embedding:
                    print(f"  [embed] {len(embedding)}-dim vector generated")

            # Create skill
            try:
                skill = await registry.create_skill(skill_create, author_id, embedding=embedding)
                print(f"  [+] skill: {skill.slug!r} (id={skill.id})")
                created += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  [error] create_skill failed: {exc}")
                errors += 1
                continue

    # -------------------------------------------------------------------
    # Seed capabilities
    # -------------------------------------------------------------------
    cap_dir = SEEDS_DIR / "capabilities"
    cap_files = sorted(cap_dir.rglob("*.yaml")) if cap_dir.exists() else []
    print(f"\nFound {len(cap_files)} capability seed files\n")

    cap_created = 0
    cap_skipped = 0
    cap_errors = 0

    # Category mapping for capabilities (not in YAML)
    CAP_CATEGORIES: dict[str, str] = {
        "comprehensive-code-review": "code-review",
        "release-documentation": "documentation",
        "secure-commit-workflow": "development/git",
    }

    async with pool.acquire() as conn:
        cap_repo = CapabilityRepo(conn)
        category_repo2 = CategoryRepo(conn)

        for yaml_path in cap_files:
            relative = yaml_path.relative_to(REPO_ROOT)
            print(f"Processing {relative} …")

            try:
                raw = yaml.safe_load(yaml_path.read_text())
            except yaml.YAMLError as exc:
                print(f"  [error] YAML parse failed: {exc}")
                cap_errors += 1
                continue

            slug = raw.get("slug", "")
            if not slug:
                print("  [error] missing 'slug' field — skipped")
                cap_errors += 1
                continue

            existing = await cap_repo.get_by_slug(slug)
            if existing is not None:
                print(f"  [skip] capability {slug!r} already exists")
                cap_skipped += 1
                continue

            cat_slug = CAP_CATEGORIES.get(slug, "development")
            await ensure_category_hierarchy(category_repo2, cat_slug)

            # Parse steps
            steps = [
                CapabilityStep(
                    skill_ref=s["skill_ref"],
                    role=s.get("role", ""),
                    inputs=s.get("inputs", {}),
                    outputs=s.get("outputs", {}),
                    required=s.get("required", True),
                    data_classification=s.get("data_classification", "none"),
                )
                for s in raw.get("steps", [])
            ]

            # Parse data flow
            data_flow = [
                DataFlowEdge(
                    from_step=e["from_step"],
                    to_step=e["to_step"],
                    classification=e.get("classification", "internal"),
                )
                for e in raw.get("data_flow", [])
            ]

            cap_create = CapabilityCreate(
                slug=slug,
                name=raw["name"],
                description=raw["description"],
                category_slug=cat_slug,
                version=raw.get("version", "1.0.0"),
                tags=raw.get("tags", []),
                scope=Scope(raw.get("scope", "community")),
                trust_tier=TrustTier(raw.get("trust_tier", "community")),
                steps=steps,
                preconditions=raw.get("preconditions", []),
                expected_outcome=raw.get("expected_outcome", ""),
                data_flow=data_flow,
                dependencies=_parse_dependencies(raw.get("dependencies", {})),
                cost_profile=CostProfile(raw.get("cost_profile", "free")),
                estimated_duration=EstimatedDuration(raw.get("estimated_duration", "slow")),
                eval_spec=_parse_eval_spec(raw.get("eval_spec", {})),
            )

            # Generate embedding
            embedding = None
            if has_embedder:
                embed_text = f"{cap_create.name}\n{cap_create.description}"
                embedding = await get_embedding(embed_text, settings)
                if embedding:
                    print(f"  [embed] {len(embedding)}-dim vector generated")

            # Resolve category to ID
            cat = await category_repo2.get_by_slug(cat_slug)
            if cat is None:
                print(f"  [error] category {cat_slug!r} not found")
                cap_errors += 1
                continue

            try:
                cap = await cap_repo.create(
                    slug=slug,
                    name=raw["name"],
                    description=raw["description"],
                    category_id=cat.id,
                    tags=raw.get("tags", []),
                    version=raw.get("version", "1.0.0"),
                    author_id=author_id,
                    steps=steps,
                    preconditions=raw.get("preconditions", []),
                    expected_outcome=raw.get("expected_outcome", ""),
                    data_flow=data_flow,
                    dependencies=_parse_dependencies(raw.get("dependencies", {})),
                    scope=Scope(raw.get("scope", "community")),
                    trust_tier=TrustTier(raw.get("trust_tier", "community")),
                    cost_profile=CostProfile(raw.get("cost_profile", "free")),
                    estimated_duration=raw.get("estimated_duration", "slow"),
                    eval_spec=_parse_eval_spec(raw.get("eval_spec", {})),
                    embedding=embedding,
                )
                print(f"  [+] capability: {cap.slug!r} (id={cap.id})")
                cap_created += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  [error] create failed: {exc}")
                cap_errors += 1

    await pool.close()

    total_errors = errors + cap_errors
    print(f"\nDone. Skills: {created} created, {skipped} skipped, {errors} errors")
    print(f"      Capabilities: {cap_created} created, {cap_skipped} skipped, {cap_errors} errors")
    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(seed())
