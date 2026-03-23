"""Arq worker for async evaluation jobs.

Started with: ``uv run arq loom.worker.WorkerSettings``
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from arq import cron  # noqa: F401 — re-exported for arq discovery
from arq.connections import RedisSettings

logger = logging.getLogger(__name__)

EVALUATOR_VERSION = "m2-v0.1.0"


async def startup(ctx: dict[str, Any]) -> None:
    """Create DB pool, LLM model, and pipeline services on worker start."""
    from loom.db.engine import create_pool
    from loom.db.repositories.eval_repo import EvalRepo
    from loom.db.repositories.skill_repo import SkillRepo
    from loom.providers.llm import create_llm_model
    from loom.services.content_isolator import isolate as isolate_content
    from loom.services.llm_evaluator import LLMEvaluator
    from loom.services.prompt_registry import PromptRegistry
    from loom.services.score_aggregator import ScoreAggregator
    from loom.services.static_analyser import StaticAnalyser
    from loom.settings import LoomSettings

    settings = LoomSettings()
    pool = await create_pool(settings.database.url)
    llm_model = create_llm_model(settings.llm)
    prompt_registry = PromptRegistry()

    from pydantic_ai import Agent

    def agent_factory(system_prompt: str) -> Agent[None, str]:
        return Agent(llm_model, system_prompt=system_prompt, output_type=str)

    static_analyser = StaticAnalyser()
    score_aggregator = ScoreAggregator()
    llm_evaluator = LLMEvaluator(
        agent_factory=agent_factory,
        prompt_registry=prompt_registry,
        model_id=settings.llm.model,
    )

    ctx["pool"] = pool
    ctx["settings"] = settings
    ctx["static_analyser"] = static_analyser
    ctx["isolate_content"] = isolate_content
    ctx["llm_evaluator"] = llm_evaluator
    ctx["score_aggregator"] = score_aggregator
    ctx["skill_repo_factory"] = lambda conn: SkillRepo(conn)
    ctx["eval_repo_factory"] = lambda conn: EvalRepo(conn)

    logger.info("Worker started — pool and pipeline services ready")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Close DB pool on worker shutdown."""
    pool = ctx.get("pool")
    if pool is not None:
        await pool.close()
    logger.info("Worker shutdown — pool closed")


async def run_eval_job(ctx: dict[str, Any], skill_id: str, trigger: str) -> dict[str, Any]:
    """Fetch skill, create eval job record, run pipeline, persist result.

    Updates the skill's eval_status and composite_score on completion.
    """
    import uuid

    from loom.services.eval_pipeline import EvalPipelineService

    pool = ctx["pool"]

    async with pool.acquire() as conn:
        skill_repo = ctx["skill_repo_factory"](conn)
        eval_repo = ctx["eval_repo_factory"](conn)

        # Fetch skill
        skill = await skill_repo.get_by_id(uuid.UUID(skill_id))
        if skill is None:
            logger.error("Skill %s not found, aborting eval job", skill_id)
            return {"error": f"Skill {skill_id} not found"}

        # Create eval job record
        job = await eval_repo.create_eval_job(
            skill_id=skill.id,
            skill_version=skill.version,
            content_hash="",  # Will be set after static analysis
            trigger_type=trigger,
            evaluator_version=EVALUATOR_VERSION,
        )

        # Mark as running
        now = datetime.now(UTC)
        await eval_repo.update_eval_job(job.id, status="running", started_at=now)

        # Update skill eval_status
        await conn.execute(
            "UPDATE skills SET eval_status = $1 WHERE id = $2",
            "running",
            skill.id,
        )

        try:
            # Build pipeline (per-request because LLMEvaluator holds agent_factory)
            pipeline = EvalPipelineService(
                static_analyser=ctx["static_analyser"],
                content_isolator=ctx["isolate_content"],
                llm_evaluator=ctx["llm_evaluator"],
                score_aggregator=ctx["score_aggregator"],
            )

            result = await pipeline.evaluate(skill)

            completed_at = datetime.now(UTC)
            await eval_repo.update_eval_job(
                job.id,
                status="completed",
                composite_score=result.composite_score,
                dimension_scores=result.dimension_scores,
                dimension_confidence=result.dimension_confidence,
                injection_flagged=result.injection_flagged,
                sandbox_passed=result.sandbox_passed,
                overall_confidence=result.overall_confidence,
                completed_at=completed_at,
            )

            # Update skill with eval results
            await conn.execute(
                """UPDATE skills
                   SET eval_status = $1,
                       composite_score = $2,
                       latest_eval_job_id = $3
                   WHERE id = $4""",
                "completed",
                result.composite_score,
                job.id,
                skill.id,
            )

            logger.info(
                "Eval job %s completed for skill %s — score=%.2f, passed=%s",
                job.id,
                skill_id,
                result.composite_score,
                result.passed,
            )
            return {
                "job_id": str(job.id),
                "passed": result.passed,
                "composite_score": result.composite_score,
            }

        except Exception:
            logger.exception("Eval job %s failed for skill %s", job.id, skill_id)
            completed_at = datetime.now(UTC)
            await eval_repo.update_eval_job(job.id, status="failed", completed_at=completed_at)
            await conn.execute(
                "UPDATE skills SET eval_status = $1 WHERE id = $2",
                "failed",
                skill.id,
            )
            raise


def _redis_settings_from_url(url: str) -> RedisSettings:
    """Parse a redis:// URL into arq RedisSettings."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or 0),
    )


class WorkerSettings:
    """Arq worker configuration.

    Started with: ``uv run arq loom.worker.WorkerSettings``
    """

    functions = [run_eval_job]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 5
    job_timeout = 120

    @staticmethod
    def redis_settings() -> RedisSettings:
        """Load Redis URL from application settings."""
        from loom.settings import LoomSettings

        settings = LoomSettings()
        return _redis_settings_from_url(settings.redis.url)
