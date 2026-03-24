"""Arq worker for async evaluation jobs.

Started with: ``uv run arq loom.worker.WorkerSettings``
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from arq import cron  # noqa: F401 — re-exported for arq discovery
from arq.connections import RedisSettings

from loom.services.score_aggregator import EVALUATOR_VERSION

logger = logging.getLogger(__name__)


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

    pipeline_cfg = settings.pipeline
    static_analyser = StaticAnalyser(
        max_content_length=pipeline_cfg.max_content_length,
        max_steps=pipeline_cfg.max_steps,
        max_dependencies=pipeline_cfg.max_dependencies,
    )
    score_aggregator = ScoreAggregator(pass_threshold=pipeline_cfg.pass_threshold)
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
    from loom.db.repositories.usage_repo import UsageRepo

    ctx["skill_repo_factory"] = lambda conn: SkillRepo(conn)
    ctx["eval_repo_factory"] = lambda conn: EvalRepo(conn)
    ctx["usage_repo_factory"] = lambda conn: UsageRepo(conn)

    # M4: Behavioral evaluation services
    from loom.db.repositories.behavioral_eval_repo import BehavioralEvalRepo
    from loom.services.behavioral_judge import BehavioralJudge
    from loom.services.behavioral_runner import BehavioralRunner

    runner_model_id = settings.pipeline.runner_model or settings.llm.model
    judge_model_id = settings.pipeline.judge_model or settings.llm.model

    behavioral_runner = BehavioralRunner(
        agent_factory=agent_factory,
        prompt_registry=prompt_registry,
        model_id=runner_model_id,
    )
    behavioral_judge = BehavioralJudge(
        agent_factory=agent_factory,
        prompt_registry=prompt_registry,
        model_id=judge_model_id,
    )

    ctx["behavioral_runner"] = behavioral_runner
    ctx["behavioral_judge"] = behavioral_judge
    ctx["behavioral_eval_repo_factory"] = lambda conn: BehavioralEvalRepo(conn)
    ctx["behavioral_runs_per_scenario"] = settings.pipeline.behavioral_runs_per_scenario

    # Create arq Redis pool for job enqueueing (used by cron jobs)
    from arq import create_pool as create_arq_pool

    ctx["redis"] = await create_arq_pool(_redis_settings_from_url(settings.redis.url))

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
    The DB connection is released before the (potentially long-running) pipeline
    evaluation and re-acquired afterwards to persist results.
    """
    import uuid

    from loom.services.eval_pipeline import EvalPipelineService

    pool = ctx["pool"]
    settings = ctx["settings"]
    runs_per_dimension: int = settings.pipeline.runs_per_dimension

    # --- Phase A: fetch skill & create job (short DB interaction) ---
    async with pool.acquire() as conn:
        skill_repo = ctx["skill_repo_factory"](conn)
        eval_repo = ctx["eval_repo_factory"](conn)

        skill = await skill_repo.get_by_id(uuid.UUID(skill_id))
        if skill is None:
            logger.error("Skill %s not found, aborting eval job", skill_id)
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
            static_analyser=ctx["static_analyser"],
            content_isolator=ctx["isolate_content"],
            llm_evaluator=ctx["llm_evaluator"],
            score_aggregator=ctx["score_aggregator"],
        )

        result, structural, raw_dimensions = await pipeline.evaluate(
            skill, runs_per_dimension=runs_per_dimension
        )

    except Exception:
        logger.exception("Eval job %s failed for skill %s", job.id, skill_id)
        # Acquire a fresh connection to persist the failure.
        async with pool.acquire() as conn:
            eval_repo = ctx["eval_repo_factory"](conn)
            skill_repo = ctx["skill_repo_factory"](conn)
            completed_at = datetime.now(UTC)
            await eval_repo.update_eval_job(job.id, status="failed", completed_at=completed_at)
            await skill_repo.update_eval_fields(skill.id, eval_status="failed")
        raise

    # --- Phase C: persist results (fresh DB connection) ---
    async with pool.acquire() as conn:
        eval_repo = ctx["eval_repo_factory"](conn)
        skill_repo = ctx["skill_repo_factory"](conn)

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
        )

    # Dispatch behavioral evaluation if the M2 pipeline passed
    if result.passed:
        redis = ctx.get("redis")
        if redis:
            await redis.enqueue_job(
                "run_behavioral_eval_job",
                skill_id,
                str(job.id),
                trigger,
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


async def run_behavioral_eval_job(
    ctx: dict[str, Any], skill_id: str, eval_job_id: str, trigger: str
) -> dict[str, Any]:
    """Run behavioral evaluation as a post-pipeline phase.

    Dispatched after M2's 5-phase pipeline passes. Runs the Runner-Judge
    loop for each scenario and persists results.
    """
    import uuid

    from loom.services.behavioral_eval_service import BehavioralEvalService

    pool = ctx["pool"]

    # Fetch skill
    async with pool.acquire() as conn:
        skill_repo = ctx["skill_repo_factory"](conn)
        skill = await skill_repo.get_by_id(uuid.UUID(skill_id))
        if skill is None:
            logger.error("Skill %s not found for behavioral eval", skill_id)
            return {"error": f"Skill {skill_id} not found"}

    # Run behavioral evaluation
    async with pool.acquire() as conn:
        behavioral_eval_repo = ctx["behavioral_eval_repo_factory"](conn)
        service = BehavioralEvalService(
            runner=ctx["behavioral_runner"],
            judge=ctx["behavioral_judge"],
            behavioral_eval_repo=behavioral_eval_repo,
            runs_per_scenario=ctx["behavioral_runs_per_scenario"],
        )

        eval_result = await service.run_evaluation(skill, uuid.UUID(eval_job_id))

    if eval_result is None:
        logger.info("Behavioral eval not applicable for skill %s", skill_id)
        return {"job_id": eval_job_id, "behavioral_score": None, "run_count": 0}

    # Persist aggregate score
    async with pool.acquire() as conn:
        eval_repo = ctx["eval_repo_factory"](conn)
        skill_repo = ctx["skill_repo_factory"](conn)

        await eval_repo.update_eval_job(
            uuid.UUID(eval_job_id),
            behavioral_score=eval_result.behavioral_score,
        )
        await skill_repo.update_eval_fields(
            skill.id,
            eval_status="completed",
            composite_score=skill.composite_score,
            latest_eval_job_id=uuid.UUID(eval_job_id),
            behavioral_score=eval_result.behavioral_score,
        )

    logger.info(
        "Behavioral eval completed for skill %s — score=%.2f, runs=%d",
        skill_id,
        eval_result.behavioral_score,
        eval_result.run_count,
    )
    return {
        "job_id": eval_job_id,
        "behavioral_score": eval_result.behavioral_score,
        "run_count": eval_result.run_count,
    }


async def scheduled_reeval(ctx: dict[str, Any]) -> dict[str, Any]:
    """Weekly cron: re-check a sample of community/verified skills.

    Selects the oldest-checked skills from community and verified tiers,
    takes a configurable sample (default 20%), and enqueues each for
    re-checking via the standard ``run_eval_job`` pipeline.
    """
    import math

    pool = ctx["pool"]
    settings: Any = ctx["settings"]
    sample_percent: float = settings.pipeline.reeval_sample_percent

    async with pool.acquire() as conn:
        skill_repo = ctx["skill_repo_factory"](conn)
        tiers = ["community", "verified"]

        total = await skill_repo.count_by_trust_tiers(tiers)
        if total == 0:
            logger.info("scheduled_reeval: no eligible skills found")
            return {"skills_sampled": 0, "total_eligible": 0}

        sample_size = max(1, math.ceil(total * sample_percent))
        candidates = await skill_repo.get_reeval_candidates(tiers, sample_size)

    # Enqueue each candidate for re-assessment
    redis = ctx.get("redis")
    enqueued = 0
    for skill in candidates:
        if redis:
            await redis.enqueue_job("run_eval_job", str(skill.id), "scheduled")
        enqueued += 1

    logger.info(
        "scheduled_reeval: enqueued %d/%d eligible skills for re-assessment",
        enqueued,
        total,
    )
    return {"skills_sampled": enqueued, "total_eligible": total}


async def aggregate_usage(ctx: dict[str, Any]) -> dict[str, Any]:
    """Hourly cron: aggregate usage reports into per-skill per-window statistics."""
    from datetime import timedelta

    pool = ctx["pool"]
    now = datetime.now(UTC)

    window_configs = [
        ("7d", 7),
        ("30d", 30),
        ("90d", 90),
    ]

    windows_processed = 0
    skills_updated = 0

    async with pool.acquire() as conn:
        usage_repo = ctx["usage_repo_factory"](conn)

        for window_type, days in window_configs:
            window_start = now - timedelta(days=days)
            pairs = await usage_repo.get_distinct_skill_versions_in_window(window_start)

            for skill_id, skill_version in pairs:
                stats = await usage_repo.aggregate_reports_in_window(
                    skill_id, skill_version, window_start
                )
                total = stats["success"] + stats["partial"] + stats["failure"]
                success_rate = stats["success"] / total if total > 0 else None

                await usage_repo.upsert_aggregate(
                    skill_id=skill_id,
                    skill_version=skill_version,
                    window_type=window_type,
                    success_count=stats["success"],
                    partial_count=stats["partial"],
                    failure_count=stats["failure"],
                    success_rate=success_rate,
                    avg_runtime_ms=stats["avg_runtime_ms"],
                    computed_at=now,
                    window_start=window_start,
                )
                skills_updated += 1

            windows_processed += 1

    logger.info(
        "aggregate_usage: processed %d windows, updated %d skill aggregates",
        windows_processed,
        skills_updated,
    )
    return {"windows_processed": windows_processed, "skills_updated": skills_updated}


async def detect_usage_signals(ctx: dict[str, Any]) -> dict[str, Any]:
    """Hourly cron: check usage aggregates for threshold violations and trigger actions."""
    pool = ctx["pool"]
    settings: Any = ctx["settings"]
    failure_rate_trigger: float = settings.pipeline.usage_failure_rate_trigger
    success_drop_trigger: float = settings.pipeline.usage_success_rate_drop_trigger

    alerts = 0
    re_evals_triggered = 0
    redis = ctx.get("redis")

    async with pool.acquire() as conn:
        usage_repo = ctx["usage_repo_factory"](conn)

        # Get 7d aggregates with at least 10 total reports
        aggregates_7d = await usage_repo.get_aggregates_above_threshold("7d", 10)

        for agg in aggregates_7d:
            total = agg.success_count + agg.partial_count + agg.failure_count
            if total == 0:
                continue

            failure_rate = agg.failure_count / total
            should_reeval = False

            # Check high failure rate
            if failure_rate > failure_rate_trigger:
                logger.warning(
                    "Signal: skill %s has %.0f%% failure rate (threshold %.0f%%)",
                    agg.skill_id,
                    failure_rate * 100,
                    failure_rate_trigger * 100,
                )
                alerts += 1
                should_reeval = True

            # Check success rate drop vs 30d
            agg_30d = await usage_repo.get_aggregate_for_skill(agg.skill_id, "30d")
            if (
                agg_30d is not None
                and agg_30d.success_rate is not None
                and agg.success_rate is not None
                and (agg_30d.success_rate - agg.success_rate) > success_drop_trigger
            ):
                logger.warning(
                    "Signal: skill %s success rate dropped %.0f%% -> %.0f%%",
                    agg.skill_id,
                    agg_30d.success_rate * 100,
                    agg.success_rate * 100,
                )
                alerts += 1
                should_reeval = True

            if should_reeval and redis:
                await redis.enqueue_job("run_eval_job", str(agg.skill_id), "usage_signal")
                re_evals_triggered += 1

    # --- Staleness detection ---
    stale_marked = 0
    staleness_days: int = settings.pipeline.staleness_window_days
    async with pool.acquire() as conn:
        skill_repo = ctx["skill_repo_factory"](conn)
        stale_ids = await skill_repo.get_stale_candidates(staleness_days)
        for sid in stale_ids:
            await skill_repo.mark_stale(sid)
            stale_marked += 1

    if stale_marked:
        logger.info("detect_usage_signals: marked %d skills as stale", stale_marked)

    logger.info(
        "detect_usage_signals: %d alerts, %d re-evaluations triggered, %d stale",
        alerts,
        re_evals_triggered,
        stale_marked,
    )
    return {
        "alerts": alerts,
        "re_evals_triggered": re_evals_triggered,
        "stale_marked": stale_marked,
    }


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

    functions = [run_eval_job, run_behavioral_eval_job]
    cron_jobs = [
        cron(scheduled_reeval, weekday={6}, hour={3}, minute={17}),
        cron(aggregate_usage, hour=None, minute={17}),  # every hour at :17
        cron(detect_usage_signals, hour=None, minute={47}),  # every hour at :47
    ]
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
