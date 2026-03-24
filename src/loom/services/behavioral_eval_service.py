"""Behavioral evaluation orchestrator — N runs per scenario with median aggregation.

Coordinates the Runner and Judge to evaluate a skill's behavioral quality.
Each scenario is run multiple times to ensure consistency. The aggregate
score uses median consensus for outlier resistance.

The evaluation is split into two phases:
  1. Inference (run_evaluation): Runs all LLM calls, collects results in-memory.
     No DB connection is needed during this phase.
  2. Persistence (persist_runs): Writes collected runs to the DB.
     Called by the worker with a fresh DB connection.
"""

from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING

from loom.models.behavioral import BehavioralEvalResult, PendingBehavioralRun
from loom.models.common import BehavioralEvalApplicability

if TYPE_CHECKING:
    import uuid as uuid_mod

    from loom.db.repositories.behavioral_eval_repo import BehavioralEvalRepo
    from loom.models.common import EvalScenario, EvalSpec, QualityDimension
    from loom.models.skill import Skill
    from loom.services.behavioral_judge import BehavioralJudge
    from loom.services.behavioral_runner import BehavioralRunner

logger = logging.getLogger(__name__)


def _should_run(eval_spec: EvalSpec, scenarios: list[EvalScenario]) -> bool:
    """Determine whether behavioral evaluation should run for this skill."""
    applicability = eval_spec.behavioral_eval

    if applicability == BehavioralEvalApplicability.NOT_APPLICABLE:
        return False

    if applicability == BehavioralEvalApplicability.REQUIRED:
        return True

    # AUTO: run only if at least one scenario has non-empty input_context
    return any(s.input_context.strip() for s in scenarios)


class BehavioralEvalService:
    """Orchestrates behavioral evaluation: N runs per scenario, aggregated scoring."""

    def __init__(
        self,
        runner: BehavioralRunner,
        judge: BehavioralJudge,
        runs_per_scenario: int = 3,
    ) -> None:
        self._runner = runner
        self._judge = judge
        self._runs_per_scenario = runs_per_scenario

    async def run_evaluation(
        self,
        skill: Skill,
        eval_job_id: uuid_mod.UUID,
    ) -> BehavioralEvalResult | None:
        """Run behavioral evaluation (inference only — no DB writes).

        Returns None if not applicable, otherwise returns results with
        pending_runs populated for later persistence.
        """
        eval_spec = skill.eval_spec
        scenarios = eval_spec.scenarios
        quality_dimensions: list[QualityDimension] = eval_spec.quality_dimensions

        if not _should_run(eval_spec, scenarios):
            logger.info("Behavioral eval not applicable for skill %s", skill.slug)
            return None

        # Filter to scenarios with non-empty input_context
        active_scenarios = [s for s in scenarios if s.input_context.strip()]
        if not active_scenarios:
            return None

        all_composites: list[float] = []
        pending_runs: list[PendingBehavioralRun] = []

        for scenario_idx, scenario in enumerate(active_scenarios):
            for run_idx in range(self._runs_per_scenario):
                # Run the skill through the Runner
                runner_output, runner_latency = await self._runner.run(skill.content, scenario)

                # Judge the output
                judge_score, judge_latency = await self._judge.judge(
                    runner_output, scenario, quality_dimensions or None
                )

                # Composite score: mean of the three axes
                composite = statistics.mean(
                    [
                        judge_score.outcome_quality,
                        judge_score.completeness,
                        judge_score.efficiency,
                    ]
                )

                # Collect run data in-memory (no DB write)
                pending_runs.append(
                    PendingBehavioralRun(
                        scenario_index=scenario_idx,
                        run_index=run_idx,
                        runner_output=runner_output,
                        judge_score=composite,
                        judge_evidence=judge_score,
                        judge_confidence=judge_score.confidence,
                        injection_detected=judge_score.injection_detected,
                        runner_model_id=self._runner.model_id,
                        judge_model_id=self._judge.model_id,
                        runner_latency_ms=runner_latency,
                        judge_latency_ms=judge_latency,
                    )
                )
                all_composites.append(composite)

        # Aggregate scores
        behavioral_score = statistics.median(all_composites)
        variance = statistics.stdev(all_composites) if len(all_composites) >= 2 else 0.0

        return BehavioralEvalResult(
            behavioral_score=behavioral_score,
            run_count=len(all_composites),
            scenario_count=len(active_scenarios),
            variance=variance,
            pending_runs=pending_runs,
        )

    @staticmethod
    async def persist_runs(
        repo: BehavioralEvalRepo,
        eval_job_id: uuid_mod.UUID,
        pending_runs: list[PendingBehavioralRun],
    ) -> None:
        """Persist collected runs to the database (Phase C)."""
        for run in pending_runs:
            await repo.create_behavioral_run(
                eval_job_id=eval_job_id,
                scenario_index=run.scenario_index,
                run_index=run.run_index,
                runner_output=run.runner_output.model_dump(),
                judge_score=run.judge_score,
                judge_evidence=run.judge_evidence.model_dump(),
                judge_confidence=run.judge_confidence,
                injection_detected=run.injection_detected,
                runner_model_id=run.runner_model_id,
                judge_model_id=run.judge_model_id,
                runner_latency_ms=run.runner_latency_ms,
                judge_latency_ms=run.judge_latency_ms,
            )
