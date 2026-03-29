#!/usr/bin/env python3
"""Ingest skills from GitHub repositories into the Loom database.

Two-step workflow:
    uv run python scripts/ingest.py --dry-run          # preview what's available
    uv run python scripts/ingest.py --approve           # actually ingest

Options:
    --repo NAME     Only process a specific repo (by repo name)
    --limit N       Cap the number of skills to ingest
    --path PREFIX   Only ingest files under a specific path prefix
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import asyncpg

# ---------------------------------------------------------------------------
# Resolve project root and add src/ to path so loom package is importable
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from typing import TYPE_CHECKING  # noqa: E402

from seed import (  # noqa: E402
    _get_embedder,
    ensure_category_hierarchy,
    ensure_seed_user,
    get_embedding,
)

from loom.db.repositories.category_repo import CategoryRepo  # noqa: E402
from loom.db.repositories.ingestion_repo import IngestionRepo  # noqa: E402
from loom.db.repositories.skill_repo import SkillRepo  # noqa: E402
from loom.db.repositories.source_artifact_repo import SourceArtifactRepo  # noqa: E402
from loom.ingestion.config import DEFAULT_REPOS, EXTENDED_REPOS  # noqa: E402
from loom.ingestion.github_scraper import GitHubScraper  # noqa: E402
from loom.ingestion.transformers import (  # noqa: E402
    compute_content_hash,
    transform_to_skill_create,
)
from loom.models.common import LifecycleState, TrustTier  # noqa: E402
from loom.services.eval import EvalService  # noqa: E402
from loom.services.registry import RegistryService  # noqa: E402
from loom.services.static_analyser import (  # noqa: E402
    MAX_CONTENT_LENGTH,
    scan_injections,
)
from loom.settings import LoomSettings  # noqa: E402

if TYPE_CHECKING:
    from loom.ingestion.config import RepoSource  # noqa: E402
    from loom.ingestion.github_scraper import RawIngestionItem  # noqa: E402
    from loom.models.skill import SkillCreate  # noqa: E402

logger = logging.getLogger(__name__)

SEED_USER_HANDLE = "loom-seed"
INGEST_MIN_CONTENT_LENGTH = 100


# ---------------------------------------------------------------------------
# DB connection setup (matches seed.py pattern)
# ---------------------------------------------------------------------------


async def _init_conn(conn: asyncpg.Connection) -> None:  # type: ignore[type-arg]
    """Set up JSONB codec and pgvector for each pool connection."""
    from pgvector.asyncpg import register_vector

    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await register_vector(conn)


# ---------------------------------------------------------------------------
# Candidate: a scraped item paired with its transform and dedup status
# ---------------------------------------------------------------------------


class Candidate:
    """A potential skill to ingest, with dedup metadata."""

    def __init__(self, item: RawIngestionItem, skill_create: SkillCreate, content_hash: str):
        self.item = item
        self.skill_create = skill_create
        self.content_hash = content_hash
        self.skip_reason: str | None = None


# ---------------------------------------------------------------------------
# Scrape + transform + dedup
# ---------------------------------------------------------------------------


async def gather_candidates(
    sources: list[RepoSource],
    scraper: GitHubScraper,
    *,
    path_prefix: str | None = None,
    limit: int | None = None,
) -> list[Candidate]:
    """Scrape repos, transform to SkillCreate, return candidates."""
    all_items: list[RawIngestionItem] = []
    remaining = limit
    for source in sources:
        items = await scraper.scrape_repo(source, limit=remaining)
        all_items.extend(items)
        if remaining is not None:
            remaining = max(0, remaining - len(items))
            if remaining == 0:
                break

    # Apply path filter
    if path_prefix:
        all_items = [i for i in all_items if i.file_path.startswith(path_prefix)]

    candidates: list[Candidate] = []
    seen_slugs: set[str] = set()

    for item in all_items:
        try:
            skill_create = transform_to_skill_create(item)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Transform failed for %s: %s", item.file_path, exc)
            continue

        content_hash = compute_content_hash(item.raw_content)

        # --- Cheap gates (Stage 1) ---
        content_len = len(skill_create.content.strip())
        if content_len < INGEST_MIN_CONTENT_LENGTH:
            c = Candidate(item, skill_create, content_hash)
            c.skip_reason = f"too short ({content_len} chars, min {INGEST_MIN_CONTENT_LENGTH})"
            candidates.append(c)
            continue
        if content_len > MAX_CONTENT_LENGTH:
            c = Candidate(item, skill_create, content_hash)
            c.skip_reason = f"too long ({content_len} chars, max {MAX_CONTENT_LENGTH})"
            candidates.append(c)
            continue
        injection_hits = scan_injections(skill_create.content)
        if injection_hits:
            c = Candidate(item, skill_create, content_hash)
            patterns = ", ".join(h.pattern for h in injection_hits)
            c.skip_reason = f"injection patterns detected: {patterns}"
            candidates.append(c)
            continue

        # Local dedup: skip duplicate slugs within this batch
        if skill_create.slug in seen_slugs:
            c = Candidate(item, skill_create, content_hash)
            c.skip_reason = "duplicate slug in batch"
            candidates.append(c)
            continue

        seen_slugs.add(skill_create.slug)
        candidates.append(Candidate(item, skill_create, content_hash))

    return candidates


async def check_db_duplicates(
    candidates: list[Candidate],
    skill_repo: SkillRepo,
    ingestion_repo: IngestionRepo,
) -> None:
    """Mark candidates that already exist in the DB."""
    for c in candidates:
        if c.skip_reason:
            continue

        # Check by content hash
        existing_ingestion = await ingestion_repo.find_by_content_hash(c.content_hash)
        if existing_ingestion is not None:
            c.skip_reason = "content hash already ingested"
            continue

        # Check by slug
        existing_skill = await skill_repo.get_by_slug(c.skill_create.slug)
        if existing_skill is not None:
            c.skip_reason = "slug already exists"
            continue


# ---------------------------------------------------------------------------
# Dry-run display
# ---------------------------------------------------------------------------


def print_dry_run(candidates: list[Candidate]) -> None:
    """Print a grouped summary of what would be ingested."""
    # Group by repo
    by_repo: dict[str, list[Candidate]] = {}
    for c in candidates:
        key = f"{c.item.repo_owner}/{c.item.repo_name}"
        by_repo.setdefault(key, []).append(c)

    new_count = sum(1 for c in candidates if c.skip_reason is None)
    skip_count = sum(1 for c in candidates if c.skip_reason is not None)

    print(f"\n{'=' * 60}")
    print(f"  DRY RUN SUMMARY: {len(candidates)} total, {new_count} new, {skip_count} skipped")
    print(f"{'=' * 60}\n")

    for repo_key, repo_candidates in by_repo.items():
        new = [c for c in repo_candidates if c.skip_reason is None]
        skipped = [c for c in repo_candidates if c.skip_reason is not None]

        print(f"  {repo_key}: {len(new)} new, {len(skipped)} skipped")

        # Show first few new items
        for c in new[:5]:
            print(f"    [new]  {c.skill_create.slug} — {c.skill_create.name[:60]}")
        if len(new) > 5:
            print(f"    ... and {len(new) - 5} more")

        # Show skip reasons
        skip_reasons: dict[str, int] = {}
        for c in skipped:
            reason = c.skip_reason or "unknown"
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
        for reason, count in skip_reasons.items():
            print(f"    [skip] {count}x {reason}")

        print()

    if new_count > 0:
        print(f"Run with --approve to ingest {new_count} new skills.\n")
    else:
        print("Nothing new to ingest.\n")


# ---------------------------------------------------------------------------
# Approve: ingest into DB
# ---------------------------------------------------------------------------


async def ingest_approved(
    candidates: list[Candidate],
    pool: asyncpg.Pool,  # type: ignore[type-arg]
    settings: LoomSettings,
) -> tuple[int, int, int]:
    """Ingest approved candidates into the database. Returns (created, skipped, errors)."""
    has_embedder = _get_embedder(settings) is not None

    # Resolve seed user with a short-lived connection
    async with pool.acquire() as conn:
        author_id = await ensure_seed_user(conn)

    created = 0
    skipped = 0
    errors = 0

    new_candidates = [c for c in candidates if c.skip_reason is None]

    for c in new_candidates:
        sc = c.skill_create
        print(f"  Ingesting {sc.slug} ...")

        # Generate embedding (no DB connection held during slow API call)
        embedding = None
        if has_embedder:
            embed_text = f"{sc.name} — {sc.description}"
            embedding = await get_embedding(embed_text, settings)
            if embedding:
                print(f"    [embed] {len(embedding)}-dim vector")

        # Acquire connection per-skill for DB operations
        async with pool.acquire() as conn:
            skill_repo = SkillRepo(conn)
            category_repo = CategoryRepo(conn)
            ingestion_repo = IngestionRepo(conn)
            eval_service = EvalService()
            registry = RegistryService(skill_repo, category_repo, eval_service)

            # Ensure category hierarchy
            try:
                await ensure_category_hierarchy(category_repo, sc.category_slug)
            except Exception as exc:  # noqa: BLE001
                print(f"    [error] category creation failed: {exc}")
                errors += 1
                continue

            # Check if skill already exists (idempotency + collision handling)
            try:
                existing = await skill_repo.get_by_slug(sc.slug)
                if existing:
                    # Same source → skip (idempotent re-run)
                    if existing.source_uri and existing.source_uri == sc.source_uri:
                        print(f"    [skip] {sc.slug} already exists (same source)")
                        skipped += 1
                        continue
                    # Different source → suffix to avoid collision
                    original_slug = sc.slug
                    suffix = c.item.source_type or "alt"
                    sc.slug = f"{sc.slug}-{suffix}"
                    # Check suffixed slug too
                    existing2 = await skill_repo.get_by_slug(sc.slug)
                    if existing2:
                        print(f"    [skip] {original_slug} collision, {sc.slug} also exists")
                        skipped += 1
                        continue
                    print(f"    [collision] {original_slug} taken, using {sc.slug}")
            except Exception:  # noqa: BLE001
                pass  # get_by_slug may raise if not found — that's fine

            # Create skill via RegistryService (skip eval validation for unvetted)
            sc.trust_tier = TrustTier.UNVETTED
            sc.lifecycle_state = LifecycleState.QUARANTINED
            sc.provenance_summary = {
                "source_type": c.item.source_type,
                "source_uri": c.item.source_uri,
                "source_ref": c.item.commit_sha,
                "status": "ingested",
            }
            try:
                skill = await registry.create_skill(
                    sc, author_id, embedding=embedding, skip_validation=True
                )
                print(f"    [+] skill created: {skill.slug} (id={skill.id})")
            except Exception as exc:  # noqa: BLE001
                print(f"    [error] create_skill failed: {exc}")
                errors += 1
                continue

            # Record provenance
            try:
                source_repo = SourceArtifactRepo(conn)
                await source_repo.create(
                    entity_kind="skill",
                    source_type=c.item.source_type,
                    source_uri=c.item.source_uri,
                    source_ref=c.item.commit_sha,
                    artifact_hash=c.content_hash,
                    raw_metadata={
                        "repo_owner": c.item.repo_owner,
                        "repo_name": c.item.repo_name,
                        "file_path": c.item.file_path,
                        "commit_sha": c.item.commit_sha,
                        "detected_license": c.item.detected_license,
                    },
                    ingest_notes={"status": "quarantined"},
                )
                await ingestion_repo.create(
                    source_type=c.item.source_type,
                    source_uri=c.item.source_uri,
                    content_hash=c.content_hash,
                    skill_id=skill.id,
                    skill_version=sc.version,
                    raw_metadata={
                        "repo_owner": c.item.repo_owner,
                        "repo_name": c.item.repo_name,
                        "file_path": c.item.file_path,
                        "commit_sha": c.item.commit_sha,
                        "detected_license": c.item.detected_license,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                print(f"    [warn] provenance record failed: {exc}")

        created += 1

    skipped = sum(1 for c in candidates if c.skip_reason is not None)
    return created, skipped, errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest skills from GitHub repositories into Loom.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Preview what would be ingested")
    mode.add_argument("--approve", action="store_true", help="Actually ingest into the database")

    parser.add_argument("--repo", type=str, default=None, help="Only process a specific repo name")
    parser.add_argument("--all", action="store_true", help="Use all repos (including extended)")
    parser.add_argument("--limit", type=int, default=None, help="Max skills to ingest")
    parser.add_argument("--path", type=str, default=None, help="Only files under this path prefix")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Filter sources
    all_sources = EXTENDED_REPOS if args.all else DEFAULT_REPOS
    sources = all_sources
    if args.repo:
        sources = [s for s in all_sources if s.repo == args.repo]
        if not sources:
            print(f"No configured repo matching {args.repo!r}")
            print(f"Available: {', '.join(s.repo for s in all_sources)}")
            sys.exit(1)

    # Create scraper
    settings = LoomSettings()
    token = settings.github_token or None
    if not token:
        print("[warn] GITHUB_TOKEN not set in .env — API rate limits will be low (60 req/hr)")
    scraper = GitHubScraper(token=token)

    try:
        # Scrape and transform
        print(f"Scraping {len(sources)} repo(s) ...")
        candidates = await gather_candidates(
            sources, scraper, path_prefix=args.path, limit=args.limit
        )
        print(f"Found {len(candidates)} candidate(s)")

        if not candidates:
            print("Nothing found. Check repo paths and patterns.")
            return

        if args.dry_run:
            # For dry-run, optionally check DB if available
            try:
                settings = LoomSettings()
                url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
                pool = await asyncpg.create_pool(url, min_size=1, max_size=2, init=_init_conn)
                assert pool is not None
                async with pool.acquire() as conn:
                    skill_repo = SkillRepo(conn)
                    ingestion_repo = IngestionRepo(conn)
                    await check_db_duplicates(candidates, skill_repo, ingestion_repo)
                await pool.close()
            except Exception:  # noqa: BLE001
                print("[info] Could not connect to DB for dedup check — showing all as new")

            print_dry_run(candidates)
            return

        # --approve: connect to DB and ingest
        settings = LoomSettings()
        from urllib.parse import urlparse

        _parsed = urlparse(settings.database.url)
        _redacted = f"{_parsed.hostname}:{_parsed.port}{_parsed.path}"
        print(f"Connecting to database: {_redacted}")
        del _parsed, _redacted
        url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
        pool = await asyncpg.create_pool(url, min_size=1, max_size=5, init=_init_conn)
        assert pool is not None

        has_embedder = _get_embedder(settings) is not None
        if has_embedder:
            print(f"Embedding provider: {settings.embedding.provider}/{settings.embedding.model}")
        else:
            print("No embedding API key — skills will be created without embeddings.")

        async with pool.acquire() as conn:
            # Check for DB duplicates
            skill_repo = SkillRepo(conn)
            ingestion_repo = IngestionRepo(conn)
            await check_db_duplicates(candidates, skill_repo, ingestion_repo)

        new_count = sum(1 for c in candidates if c.skip_reason is None)
        skip_count = sum(1 for c in candidates if c.skip_reason is not None)
        print(f"\n{new_count} new skills to ingest, {skip_count} to skip\n")

        if new_count == 0:
            print("Nothing new to ingest.")
            await pool.close()
            return

        created, skipped, errors = await ingest_approved(candidates, pool, settings)

        await pool.close()

        print(f"\nDone. {created} created, {skipped} skipped, {errors} errors")
        if errors:
            sys.exit(1)

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
