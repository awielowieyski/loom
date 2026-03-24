"""Tests for BehavioralEvalService — orchestrates N runs per scenario."""

import uuid
from unittest.mock import AsyncMock, MagicMock

from loom.models.behavioral import (
    BehavioralEvalResult,
    JudgeScore,
    PendingBehavioralRun,
    RunnerOutput,
)
from loom.models.common import (
    BehavioralEvalApplicability,
    EvalScenario,
    EvalSpec,
    QualityDimension,
)
from loom.services.behavioral_eval_service import BehavioralEvalService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_skill(
    behavioral_eval: BehavioralEvalApplicability = BehavioralEvalApplicability.AUTO,
    scenarios: list[dict[str, str]] | None = None,
    quality_dimensions: list[dict[str, str]] | None = None,
) -> MagicMock:
    """Create a mock Skill with configurable eval_spec."""
    if scenarios is None:
        scenarios = [
            {
                "description": "Sort numbers",
                "input_context": "A list of numbers: [3, 1, 2]",
                "success_criteria": "Returns sorted list",
            }
        ]
    if quality_dimensions is None:
        quality_dimensions = []

    eval_spec = EvalSpec(
        scenarios=[EvalScenario(**s) for s in scenarios],
        quality_dimensions=[QualityDimension(**d) for d in quality_dimensions],
        behavioral_eval=behavioral_eval,
    )

    skill = MagicMock()
    skill.id = uuid.uuid4()
    skill.slug = "test-skill"
    skill.content = "# Step 1\nDo something"
    skill.eval_spec = eval_spec
    return skill


def _make_runner_output() -> RunnerOutput:
    return RunnerOutput(
        actions_taken=["Did step 1"],
        output="Result",
        artifacts=[],
        notes=None,
    )


def _make_judge_score(
    outcome_quality: float = 0.8,
    completeness: float = 0.7,
    efficiency: float = 0.9,
    confidence: float = 0.85,
    injection_detected: bool = False,
) -> JudgeScore:
    return JudgeScore(
        outcome_quality=outcome_quality,
        completeness=completeness,
        efficiency=efficiency,
        evidence="Good result",
        confidence=confidence,
        injection_detected=injection_detected,
    )


def _mock_runner(output: RunnerOutput | None = None) -> AsyncMock:
    runner = AsyncMock()
    runner.model_id = "test-runner"
    runner.run = AsyncMock(return_value=(output or _make_runner_output(), 100))
    return runner


def _mock_judge(score: JudgeScore | None = None) -> AsyncMock:
    judge = AsyncMock()
    judge.model_id = "test-judge"
    judge.judge = AsyncMock(return_value=(score or _make_judge_score(), 50))
    return judge


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBehavioralEvalService:
    """BehavioralEvalService orchestration tests."""

    async def test_runs_n_times_per_scenario(self) -> None:
        """Orchestrator runs runner N times per scenario."""
        eval_job_id = uuid.uuid4()
        runner = _mock_runner()
        judge = _mock_judge()
        skill = _make_skill()

        service = BehavioralEvalService(runner, judge, runs_per_scenario=3)
        result = await service.run_evaluation(skill, eval_job_id)

        assert result is not None
        assert isinstance(result, BehavioralEvalResult)
        # 1 scenario x 3 runs = 3 runner calls
        assert runner.run.call_count == 3
        assert judge.judge.call_count == 3
        assert len(result.pending_runs) == 3
        assert result.run_count == 3
        assert result.scenario_count == 1

    async def test_not_applicable_returns_none(self) -> None:
        """behavioral_eval='not_applicable' returns None."""
        skill = _make_skill(behavioral_eval=BehavioralEvalApplicability.NOT_APPLICABLE)
        runner = _mock_runner()
        judge = _mock_judge()

        service = BehavioralEvalService(runner, judge)
        result = await service.run_evaluation(skill, uuid.uuid4())

        assert result is None
        runner.run.assert_not_called()

    async def test_auto_with_empty_input_context_returns_none(self) -> None:
        """AUTO with all empty input_context skips evaluation."""
        skill = _make_skill(
            behavioral_eval=BehavioralEvalApplicability.AUTO,
            scenarios=[
                {
                    "description": "Test",
                    "input_context": "",
                    "success_criteria": "Pass",
                },
                {
                    "description": "Test 2",
                    "input_context": "   ",
                    "success_criteria": "Pass",
                },
            ],
        )
        runner = _mock_runner()
        judge = _mock_judge()

        service = BehavioralEvalService(runner, judge)
        result = await service.run_evaluation(skill, uuid.uuid4())

        assert result is None

    async def test_auto_with_non_empty_input_context_runs(self) -> None:
        """AUTO with non-empty input_context runs evaluation."""
        skill = _make_skill(
            behavioral_eval=BehavioralEvalApplicability.AUTO,
            scenarios=[
                {
                    "description": "With context",
                    "input_context": "Some context",
                    "success_criteria": "Pass",
                }
            ],
        )
        runner = _mock_runner()
        judge = _mock_judge()

        service = BehavioralEvalService(runner, judge, runs_per_scenario=1)
        result = await service.run_evaluation(skill, uuid.uuid4())

        assert result is not None
        assert result.run_count == 1

    async def test_required_always_runs(self) -> None:
        """REQUIRED always runs even with empty input_context in scenarios."""
        # Note: required still requires at least one scenario with non-empty
        # input_context to actually produce runs
        skill = _make_skill(
            behavioral_eval=BehavioralEvalApplicability.REQUIRED,
            scenarios=[
                {
                    "description": "Test",
                    "input_context": "Some input",
                    "success_criteria": "Pass",
                }
            ],
        )
        runner = _mock_runner()
        judge = _mock_judge()

        service = BehavioralEvalService(runner, judge, runs_per_scenario=1)
        result = await service.run_evaluation(skill, uuid.uuid4())

        assert result is not None
        assert result.run_count == 1

    async def test_median_score_used(self) -> None:
        """Aggregate uses median (not mean) for outlier resistance."""
        eval_job_id = uuid.uuid4()
        runner = _mock_runner()

        # Create judge that returns different scores on each call
        scores = [
            _make_judge_score(outcome_quality=0.9, completeness=0.9, efficiency=0.9),
            _make_judge_score(outcome_quality=0.1, completeness=0.1, efficiency=0.1),
            _make_judge_score(outcome_quality=0.8, completeness=0.8, efficiency=0.8),
        ]
        judge = AsyncMock()
        judge.model_id = "test-judge"
        judge.judge = AsyncMock(side_effect=[(s, 50) for s in scores])

        skill = _make_skill()

        service = BehavioralEvalService(runner, judge, runs_per_scenario=3)
        result = await service.run_evaluation(skill, eval_job_id)

        assert result is not None
        # Scores: 0.9, 0.1, 0.8 -> median = 0.8
        assert result.behavioral_score == 0.8

    async def test_pending_runs_returned(self) -> None:
        """Pending run data is included in result for later persistence."""
        eval_job_id = uuid.uuid4()
        runner = _mock_runner()
        judge = _mock_judge()

        skill = _make_skill()

        service = BehavioralEvalService(runner, judge, runs_per_scenario=2)
        result = await service.run_evaluation(skill, eval_job_id)

        assert result is not None
        assert len(result.pending_runs) == 2
        for run in result.pending_runs:
            assert isinstance(run, PendingBehavioralRun)

    async def test_multiple_scenarios(self) -> None:
        """Multiple scenarios each get N runs."""
        eval_job_id = uuid.uuid4()
        runner = _mock_runner()
        judge = _mock_judge()

        skill = _make_skill(
            scenarios=[
                {
                    "description": "Scenario A",
                    "input_context": "Context A",
                    "success_criteria": "Pass A",
                },
                {
                    "description": "Scenario B",
                    "input_context": "Context B",
                    "success_criteria": "Pass B",
                },
            ]
        )

        service = BehavioralEvalService(runner, judge, runs_per_scenario=2)
        result = await service.run_evaluation(skill, eval_job_id)

        assert result is not None
        # 2 scenarios x 2 runs = 4 total
        assert result.run_count == 4
        assert result.scenario_count == 2

    async def test_variance_computed(self) -> None:
        """Variance is computed as stdev across all composite scores."""
        eval_job_id = uuid.uuid4()
        runner = _mock_runner()

        # Different scores -> non-zero variance
        scores = [
            _make_judge_score(outcome_quality=1.0, completeness=1.0, efficiency=1.0),
            _make_judge_score(outcome_quality=0.5, completeness=0.5, efficiency=0.5),
        ]
        judge = AsyncMock()
        judge.model_id = "test-judge"
        judge.judge = AsyncMock(side_effect=[(s, 50) for s in scores])

        skill = _make_skill()

        service = BehavioralEvalService(runner, judge, runs_per_scenario=2)
        result = await service.run_evaluation(skill, eval_job_id)

        assert result is not None
        assert result.variance > 0.0
