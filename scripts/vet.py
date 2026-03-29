#!/usr/bin/env python3
"""Vet unvetted skills: LLM meta rewrite → eval → promote or reject.

This is Pass 2 of the two-pass ingestion pipeline.
Skills must already be in the DB with trust_tier='unvetted' (from ingest.py).

Usage:
    uv run python scripts/vet.py --batch 5          # vet 5 oldest unvetted skills
    uv run python scripts/vet.py --batch 5 --dry-run # show what would be rewritten
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

# ---------------------------------------------------------------------------
# Resolve project root
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncpg  # noqa: E402
from pgvector.asyncpg import register_vector  # noqa: E402
from pydantic_ai import Agent  # noqa: E402
from seed import get_embedding  # noqa: E402

from loom.db.repositories.eval_repo import EvalRepo  # noqa: E402
from loom.db.repositories.service_metadata_repo import ServiceMetadataRepo  # noqa: E402
from loom.db.repositories.skill_repo import SkillRepo  # noqa: E402
from loom.models.common import (  # noqa: E402
    AuthorshipStatus,
    CanonicalizationLevel,
    EvalScenario,
    EvalSpec,
    LifecycleState,
    TrustTier,
)
from loom.providers.llm import create_llm_model  # noqa: E402
from loom.services.eval_runner import run_evaluation  # noqa: E402
from loom.services.service_metadata_extractor import extract_service_metadata  # noqa: E402
from loom.settings import LoomSettings  # noqa: E402

if TYPE_CHECKING:
    import uuid as uuid_mod

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB connection setup (matches ingest.py / seed.py pattern)
# ---------------------------------------------------------------------------


async def _init_conn(conn: asyncpg.Connection) -> None:  # type: ignore[type-arg]
    """Set up JSONB codec and pgvector for each pool connection."""
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await register_vector(conn)


# ---------------------------------------------------------------------------
# Meta rewrite prompt
# ---------------------------------------------------------------------------
META_REWRITE_SYSTEM = textwrap.dedent("""\
You are a skill librarian for Loom, a registry of AI agent skills.
Your job is to analyse a raw skill and produce structured metadata
that makes it discoverable, distinguishable, and evaluable.

You will receive:
1. The full skill content (markdown)
2. Descriptions of the 5 most similar existing skills in the registry

Produce a JSON object with these fields:
- "name": A clear, descriptive name (2-8 words). No author handles or branding.
- "description": 1-2 sentences describing what the skill does, when to use it,
  and what it does NOT do. Be specific enough to distinguish from similar skills.
- "embedding_text": A search-optimised paragraph (30-60 words) that an agent would
  use to find this skill. Include the problem domain, use case, and key differentiators.
  Include negative framing ("does NOT handle X") if similar skills exist.
- "eval_scenarios": An array of 3-5 test scenarios, each with:
  - "description": what the scenario tests
  - "input_context": a realistic user request that would trigger this skill
  - "success_criteria": concrete, verifiable criteria for a good result
- "category": A slash-separated category path (e.g. "development/testing",
  "devops/ci", "documentation/api"). Use lowercase.
- "tags": 3-8 lowercase tags for filtering.

Return ONLY valid JSON. No markdown fencing, no explanation.
""")


def _build_rewrite_prompt(skill_content: str, similar_descriptions: list[str]) -> str:
    """Build the user message for the meta rewrite LLM call."""
    similar_block = "\n".join(f"  {i + 1}. {desc}" for i, desc in enumerate(similar_descriptions))
    if not similar_block:
        similar_block = "  (no similar skills in registry yet)"

    return textwrap.dedent(f"""\
## Skill Content

{skill_content[:8000]}

## Most Similar Existing Skills

{similar_block}

Produce the JSON metadata object.
""")


async def rewrite_metadata(
    agent: Agent[None, str],
    skill_content: str,
    similar_descriptions: list[str],
) -> dict:
    """Call the LLM to generate rewritten metadata for a skill."""
    prompt = _build_rewrite_prompt(skill_content, similar_descriptions)
    result = await agent.run(prompt)
    text = result.output.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    if text.startswith("json"):
        text = text[4:]
    return json.loads(text.strip())


async def find_similar_skills(
    pool: asyncpg.pool.Pool,
    embedding: list[float],
    exclude_id: str,
    limit: int = 5,
) -> list[str]:
    """Find descriptions of the N most similar vetted skills."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT name, description FROM skills
            WHERE lifecycle_state = 'published'
              AND embedding IS NOT NULL
              AND id != $1
            ORDER BY embedding <=> $2::vector
            LIMIT $3
            """,
            exclude_id,
            embedding,
            limit,
        )
    return [f"{r['name']}: {r['description']}" for r in rows]


async def vet_skill(
    pool: asyncpg.pool.Pool,
    skill_id: uuid_mod.UUID,
    skill_slug: str,
    skill_content: str,
    skill_embedding: list[float] | None,
    source_uri: str | None,
    rewrite_agent: Agent[None, str],
    settings: LoomSettings,
    *,
    dry_run: bool = False,
) -> dict:
    """Run the full vetting pipeline on a single skill.

    Returns a summary dict with the outcome.
    """
    result = {"slug": skill_slug, "status": "unknown", "details": {}}

    # Step 1: Find similar skills for disambiguation context
    similar: list[str] = []
    if skill_embedding:
        similar = await find_similar_skills(pool, skill_embedding, skill_id)

    # Step 2: LLM meta rewrite
    print(f"  [{skill_slug}] Generating metadata rewrite...")
    try:
        meta = await rewrite_metadata(rewrite_agent, skill_content, similar)
    except (json.JSONDecodeError, Exception) as exc:  # noqa: BLE001
        result["status"] = "rewrite_failed"
        result["details"] = {"error": str(exc)}
        print(f"    [!] Rewrite failed: {exc}")
        return result

    new_name = meta.get("name", skill_slug)
    new_desc = meta.get("description", "")
    embedding_text = meta.get("embedding_text", f"{new_name} — {new_desc}")
    raw_scenarios = meta.get("eval_scenarios", [])
    new_tags = meta.get("tags", [])

    print(f"    Name: {new_name}")
    print(f"    Desc: {new_desc[:100]}...")
    print(f"    Scenarios: {len(raw_scenarios)}")

    if dry_run:
        result["status"] = "dry_run"
        result["details"] = meta
        return result

    # Step 3: Generate new embedding from discriminative text
    print(f"  [{skill_slug}] Generating discriminative embedding...")
    new_embedding = await get_embedding(embedding_text, settings)

    # Step 4: Build eval scenarios and update skill metadata
    scenarios = []
    for s in raw_scenarios[:5]:
        # LLM sometimes returns success_criteria as a list — join to string
        criteria = s.get("success_criteria", "")
        if isinstance(criteria, list):
            criteria = "; ".join(str(c) for c in criteria)
        scenarios.append(
            EvalScenario(
                description=str(s.get("description", "")),
                input_context=str(s.get("input_context", "")),
                success_criteria=str(criteria),
            )
        )

    if not scenarios:
        result["status"] = "no_scenarios"
        result["details"] = {"error": "LLM generated 0 eval scenarios"}
        print("    [!] No eval scenarios generated, skipping")
        return result

    eval_spec = EvalSpec(scenarios=scenarios)

    async with pool.acquire() as conn:
        skill_repo = SkillRepo(conn)
        await skill_repo.update_metadata(
            skill_id,
            name=new_name,
            description=new_desc,
            tags=new_tags,
            embedding=new_embedding,
            embedding_text=embedding_text,
            eval_spec=eval_spec,
            lifecycle_state=LifecycleState.EVALUATING,
            canonicalization_level=CanonicalizationLevel.SUBSTANTIVE,
            authorship_status=AuthorshipStatus.LOOM_AMENDED,
            change_type="loom_canonicalize",
            change_agent="loom/canonicalizer",
            change_rationale="Metadata canonicalized before publication",
        )
        version_id = await conn.fetchval(
            "SELECT current_version_id FROM skills WHERE id = $1", skill_id
        )
        if version_id is not None:
            service_repo = ServiceMetadataRepo(conn)
            dependencies, pricing_facts, setup_requirements = extract_service_metadata(
                skill_content=skill_content,
                source_uri=source_uri,
            )
            await service_repo.replace_skill_version_metadata(
                skill_version_id=version_id,
                dependencies=dependencies,
                pricing_facts=pricing_facts,
                setup_requirements=setup_requirements,
            )

    # Step 5: Run full eval pipeline
    print(f"  [{skill_slug}] Running evaluation pipeline...")
    try:
        eval_result = await run_evaluation(pool, skill_id, trigger="vet_pipeline")
        passed = eval_result.get("passed", False)
        score = eval_result.get("composite_score", 0)
        print(f"    Score: {score:.2f}, Passed: {passed}")

        # If eval passes, publish as experimental
        if passed:
            async with pool.acquire() as conn:
                skill_repo = SkillRepo(conn)
                eval_repo = EvalRepo(conn)
                await skill_repo.update_metadata(
                    skill_id,
                    lifecycle_state=LifecycleState.PUBLISHED,
                    change_type="loom_publish",
                    change_agent="loom/publisher",
                    change_rationale="Initial published canonical release",
                )
                await skill_repo.update_trust_tier(skill_id, TrustTier.EXPERIMENTAL)
                await eval_repo.create_trust_audit_entry(
                    skill_id=skill_id,
                    previous_tier="unvetted",
                    new_tier="experimental",
                    reason="Vet pipeline: canonical release published",
                )
            result["status"] = "promoted"
        else:
            # Failed eval — mark rejected and keep it hidden
            async with pool.acquire() as conn:
                skill_repo = SkillRepo(conn)
                await skill_repo.update_metadata(
                    skill_id,
                    lifecycle_state=LifecycleState.REJECTED,
                    change_type="loom_reject",
                    change_agent="loom/publisher",
                    change_rationale="Canonical draft failed evaluation",
                )
            result["status"] = "evaluated_low_score"

        result["details"] = {
            "name": new_name,
            "description": new_desc,
            "score": score,
            "passed": passed,
            "scenarios": len(scenarios),
        }

    except Exception as exc:  # noqa: BLE001
        import traceback

        # Eval failed — mark rejected and keep it hidden
        try:
            async with pool.acquire() as conn:
                skill_repo = SkillRepo(conn)
                await skill_repo.update_metadata(
                    skill_id,
                    lifecycle_state=LifecycleState.REJECTED,
                    change_type="loom_reject",
                    change_agent="loom/publisher",
                    change_rationale=f"Canonical draft evaluation exception: {exc}",
                )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to demote skill %s after eval error", skill_id)

        result["status"] = "eval_failed"
        result["details"] = {"error": str(exc)}
        print(f"    [!] Eval failed: {exc}")
        traceback.print_exc()

    return result


async def main() -> None:
    parser = argparse.ArgumentParser(description="Vet unvetted skills")
    parser.add_argument("--batch", type=int, default=5, help="Number of skills to vet")
    parser.add_argument("--dry-run", action="store_true", help="Show rewrites without applying")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    settings = LoomSettings()
    # asyncpg wants plain postgresql:// not postgresql+asyncpg://
    db_url = settings.database.url.replace("+asyncpg", "")
    pool = await asyncpg.create_pool(db_url, init=_init_conn)

    # Fetch unvetted skills
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, slug, content, embedding, source_uri
            FROM skills
            WHERE trust_tier = 'unvetted'
            ORDER BY created_at ASC
            LIMIT $1
            """,
            args.batch,
        )

    if not rows:
        print("No unvetted skills found.")
        await pool.close()
        return

    print(f"Found {len(rows)} unvetted skill(s) to vet.\n")

    # Build LLM agent for meta rewrite
    llm_model = create_llm_model(settings.llm)
    rewrite_agent = Agent(llm_model, system_prompt=META_REWRITE_SYSTEM, output_type=str)

    # Process each skill
    results = []
    for row in rows:
        skill_id = row["id"]
        skill_slug = row["slug"]
        skill_content = row["content"]
        # asyncpg may return embedding as string or None
        raw_emb = row["embedding"]
        skill_embedding = None
        if raw_emb is not None:
            if isinstance(raw_emb, str):
                # pgvector returns "[1,2,3]" string
                skill_embedding = json.loads(raw_emb)
            elif hasattr(raw_emb, "tolist"):
                skill_embedding = raw_emb.tolist()
            else:
                skill_embedding = list(raw_emb)

        print(f"Vetting: {skill_slug}")
        r = await vet_skill(
            pool=pool,
            skill_id=skill_id,
            skill_slug=skill_slug,
            skill_content=skill_content,
            skill_embedding=skill_embedding,
            source_uri=row["source_uri"],
            rewrite_agent=rewrite_agent,
            settings=settings,
            dry_run=args.dry_run,
        )
        results.append(r)
        print()

    # Summary
    print("=" * 60)
    print("  VET SUMMARY")
    print("=" * 60)
    for r in results:
        status_icon = {
            "promoted": "✅",
            "evaluated_low_score": "⚠️",
            "dry_run": "👀",
            "rewrite_failed": "❌",
            "eval_failed": "❌",
            "no_scenarios": "❌",
        }.get(r["status"], "❓")
        score_str = ""
        if "score" in r.get("details", {}):
            score_str = f" (score: {r['details']['score']:.2f})"
        print(f"  {status_icon} {r['slug']}: {r['status']}{score_str}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
