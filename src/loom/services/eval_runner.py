"""Reusable evaluation runner — can be called from worker, CLI, or API.

Extracts the 3-phase eval pattern (DB fetch, pipeline run, persist results)
into a standalone async function that accepts a connection pool.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from loom.services.score_aggregator import EVALUATOR_VERSION

if TYPE_CHECKING:
    import asyncpg

    from loom.services.llm_evaluator import LLMEvaluator
    from loom.services.score_aggregator import ScoreAggregator
    from loom.services.static_analyser import StaticAnalyser

logger = logging.getLogger(__name__)


async def run_evaluation(
    pool: asyncpg.pool.Pool,
    skill_id: str | uuid.UUID,
    trigger: str,
    *,
    static_analyser: StaticAnalyser | None = None,
    llm_evaluator: LLMEvaluator | None = None,
    score_aggregator: ScoreAggregator | None = None,
    runs_per_dimension: int = 3,
    enqueue_behavioral: bool = False,
) -> dict[str, Any]:
    """Run a full evaluation on a skill.

    Can be called from the arq worker, a CLI script, or any async context.
    Follows the same 3-phase pattern as the worker: fetch, evaluate, persist.

    Args:
        pool: asyncpg connection pool (connections are acquired/released per phase).
        skill_id: UUID of the skill to evaluate.
        trigger: Trigger type string (e.g. "manual", "api", "scheduled").
        static_analyser: Optional pre-built StaticAnalyser (created from settings if None).
        llm_evaluator: Optional pre-built LLMEvaluator (created from settings if None).
        score_aggregator: Optional pre-built ScoreAggregator (created from settings if None).
        runs_per_dimension: Number of LLM evaluation runs per dimension.
        enqueue_behavioral: If True, dispatch behavioral eval via Redis after pass.

    Returns:
        Dict with keys: job_id, passed, composite_score.
    """
    from loom.db.repositories.eval_repo import EvalRepo
    from loom.db.repositories.skill_repo import SkillRepo
    from loom.services.content_isolator import isolate as isolate_content
    from loom.services.eval_pipeline import EvalPipelineService

    # Build default services from settings if not provided
    if static_analyser is None or llm_evaluator is None or score_aggregator is None:
        static_analyser, llm_evaluator, score_aggregator = _create_default_services(
            static_analyser=static_analyser,
            llm_evaluator=llm_evaluator,
            score_aggregator=score_aggregator,
        )

    sid = uuid.UUID(str(skill_id))

    # --- Phase A: fetch skill & create job (short DB interaction) ---
    async with pool.acquire() as conn:
        skill_repo = SkillRepo(conn)
        eval_repo = EvalRepo(conn)

        skill = await skill_repo.get_by_id(sid)
        if skill is None:
            logger.error("Skill %s not found, aborting eval", skill_id)
            return {"error": f"Skill {skill_id} not found"}

        job = await eval_repo.create_eval_job(
            skill_id=skill.id,
            skill_version=skill.version,
            content_hash="",
            trigger_type=trigger,
            evaluator_version=EVALUATOR_VERSION,
        )

        now = datetime.now(UTC)
        await eval_repo.update_eval_job(job.id, status="running", started_at=now)
        await skill_repo.update_eval_fields(skill.id, eval_status="running")

    # --- Phase B: run pipeline (no DB connection held) ---
    try:
        pipeline = EvalPipelineService(
            static_analyser=static_analyser,
            content_isolator=isolate_content,
            llm_evaluator=llm_evaluator,
            score_aggregator=score_aggregator,
        )

        result, structural, raw_dimensions = await pipeline.evaluate(
            skill, runs_per_dimension=runs_per_dimension
        )

    except Exception:
        logger.exception("Eval failed for skill %s (job %s)", skill_id, job.id)
        async with pool.acquire() as conn:
            eval_repo = EvalRepo(conn)
            skill_repo = SkillRepo(conn)
            completed_at = datetime.now(UTC)
            await eval_repo.update_eval_job(job.id, status="failed", completed_at=completed_at)
            await skill_repo.update_eval_fields(skill.id, eval_status="failed")
        raise

    # --- Phase C: persist results (fresh DB connection) ---
    async with pool.acquire() as conn:
        eval_repo = EvalRepo(conn)
        skill_repo = SkillRepo(conn)

        for dim, runs in raw_dimensions.items():
            for idx, run in enumerate(runs):
                await eval_repo.create_dimension_run(
                    eval_job_id=job.id,
                    dimension=dim.value,
                    run_index=idx,
                    score=run.score,
                    evidence=run.evidence,
                    injection_detected=run.injection_detected,
                    injection_detail=run.injection_detail,
                    confidence=run.confidence,
                )

        completed_at = datetime.now(UTC)
        await eval_repo.update_eval_job(
            job.id,
            status="completed",
            content_hash=result.content_hash,
            structural_report=structural.model_dump(),
            composite_score=result.composite_score,
            dimension_scores=result.dimension_scores,
            dimension_confidence=result.dimension_confidence,
            injection_flagged=result.injection_flagged,
            sandbox_passed=result.sandbox_passed,
            overall_confidence=result.overall_confidence,
            completed_at=completed_at,
        )

        await skill_repo.update_eval_fields(
            skill.id,
            eval_status="completed",
            composite_score=result.composite_score,
            latest_eval_job_id=job.id,
            last_eval_at=datetime.now(UTC),
        )

    logger.info(
        "Eval completed for skill %s (job %s) — score=%.2f, passed=%s",
        skill_id,
        job.id,
        result.composite_score,
        result.passed,
    )
    return {
        "job_id": str(job.id),
        "passed": result.passed,
        "composite_score": result.composite_score,
    }


def _create_default_services(
    *,
    static_analyser: StaticAnalyser | None,
    llm_evaluator: LLMEvaluator | None,
    score_aggregator: ScoreAggregator | None,
) -> tuple[StaticAnalyser, LLMEvaluator, ScoreAggregator]:
    """Build pipeline services from settings, reusing any that were provided."""
    from pydantic_ai import Agent

    from loom.providers.llm import create_llm_model
    from loom.services.llm_evaluator import LLMEvaluator as LLMEvaluatorClass
    from loom.services.prompt_registry import PromptRegistry
    from loom.services.score_aggregator import ScoreAggregator as ScoreAggregatorClass
    from loom.services.static_analyser import StaticAnalyser as StaticAnalyserClass
    from loom.settings import LoomSettings

    settings = LoomSettings()
    pipeline_cfg = settings.pipeline

    if static_analyser is None:
        static_analyser = StaticAnalyserClass(
            max_content_length=pipeline_cfg.max_content_length,
            max_steps=pipeline_cfg.max_steps,
            max_dependencies=pipeline_cfg.max_dependencies,
        )

    if score_aggregator is None:
        score_aggregator = ScoreAggregatorClass(pass_threshold=pipeline_cfg.pass_threshold)

    if llm_evaluator is None:
        llm_model = create_llm_model(settings.llm)
        prompt_registry = PromptRegistry()

        def agent_factory(system_prompt: str) -> Agent[None, str]:
            return Agent(llm_model, system_prompt=system_prompt, output_type=str)

        llm_evaluator = LLMEvaluatorClass(
            agent_factory=agent_factory,
            prompt_registry=prompt_registry,
            model_id=settings.llm.model,
        )

    return static_analyser, llm_evaluator, score_aggregator
