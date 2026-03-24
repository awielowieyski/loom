"""Tests for ComparativeEvalService — blind head-to-head skill comparison."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from loom.models.behavioral import (
    ComparativeAxisScores,
    ComparativeResult,
    ComparisonSummary,
)
from loom.models.common import EvalScenario, EvalSpec, QualityDimension
from loom.services.comparative_eval import ComparativeEvalService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_skill(
    skill_id: uuid.UUID | None = None,
    slug: str = "test-skill",
    content: str = "# Step 1\nDo something",
    version: str = "1.0.0",
    scenarios: list[dict[str, str]] | None = None,
    quality_dimensions: list[dict[str, str]] | None = None,
) -> MagicMock:
    """Create a mock Skill for comparative evaluation."""
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
    )

    skill = MagicMock()
    skill.id = skill_id or uuid.uuid4()
    skill.slug = slug
    skill.content = content
    skill.version = version
    skill.eval_spec = eval_spec
    return skill


def _make_runner_output(output: str = "Result") -> MagicMock:
    """Create a RunnerOutput-like mock with model_dump."""
    ro = MagicMock()
    ro.model_dump.return_value = {
        "actions_taken": ["Did step 1"],
        "output": output,
        "artifacts": [],
        "notes": None,
    }
    return ro


def _make_judge_response(
    preference: str = "X",
    confidence: float = 0.75,
    score_x: dict | None = None,
    score_y: dict | None = None,
) -> str:
    """Build a JSON string mimicking the comparative judge LLM response."""
    return json.dumps(
        {
            "score_x": score_x
            or {
                "outcome_quality": 0.8,
                "completeness": 0.7,
                "efficiency": 0.9,
                "safety": 1.0,
            },
            "score_y": score_y
            or {
                "outcome_quality": 0.6,
                "completeness": 0.5,
                "efficiency": 0.7,
                "safety": 1.0,
            },
            "preference": preference,
            "confidence": confidence,
            "reasoning": "X was better overall",
        }
    )


def _mock_runner() -> AsyncMock:
    """Runner that returns a fresh RunnerOutput per call."""
    runner = AsyncMock()
    runner._model_id = "test-runner"
    runner.run = AsyncMock(
        side_effect=lambda content, scenario: (_make_runner_output(content), 100)
    )
    return runner


def _mock_prompt_registry() -> MagicMock:
    registry = MagicMock()
    variant = MagicMock()
    variant.system_prompt = "You are a comparative judge."
    registry.get_behavioral_variant.return_value = variant
    return registry


def _mock_agent_factory(judge_response: str) -> MagicMock:
    """Factory that returns an agent whose .run() returns the given JSON."""
    agent = MagicMock()
    result = MagicMock()
    result.output = judge_response
    agent.run = AsyncMock(return_value=result)

    factory = MagicMock(return_value=agent)
    return factory


def _mock_repo() -> AsyncMock:
    """Mock BehavioralEvalRepo that returns ComparativeResult from kwargs."""
    repo = AsyncMock()

    async def create_comparative(**kwargs):  # type: ignore[no-untyped-def]
        return ComparativeResult(
            id=uuid.uuid4(),
            skill_a_id=kwargs["skill_a_id"],
            skill_a_version=kwargs["skill_a_version"],
            skill_b_id=kwargs["skill_b_id"],
            skill_b_version=kwargs["skill_b_version"],
            scenario_index=kwargs["scenario_index"],
            winner=kwargs["winner"],
            score_a=ComparativeAxisScores(**kwargs["score_a"]),
            score_b=ComparativeAxisScores(**kwargs["score_b"]),
            preference_confidence=kwargs["preference_confidence"],
            reasoning=kwargs["reasoning"],
            judge_model_id=kwargs["judge_model_id"],
        )

    repo.create_comparative_result = AsyncMock(side_effect=create_comparative)
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestComparativeEvalService:
    """ComparativeEvalService tests."""

    async def test_both_skills_run_through_runner(self) -> None:
        """Both skills are run through the Runner on the same scenario."""
        runner = _mock_runner()
        repo = _mock_repo()
        judge_resp = _make_judge_response()
        factory = _mock_agent_factory(judge_resp)

        skill_a = _make_skill(slug="skill-a", content="content-a")
        skill_b = _make_skill(slug="skill-b", content="content-b")
        scenarios = skill_a.eval_spec.scenarios

        service = ComparativeEvalService(
            runner=runner,
            prompt_registry=_mock_prompt_registry(),
            agent_factory=factory,
            model_id="test-model",
            behavioral_eval_repo=repo,
        )

        result = await service.compare(skill_a, skill_b, scenarios)

        assert isinstance(result, ComparisonSummary)
        assert runner.run.call_count == 2  # once per skill

    async def test_judge_receives_anonymised_outputs(self) -> None:
        """Judge receives outputs labelled as output_x and output_y, not a/b."""
        runner = _mock_runner()
        repo = _mock_repo()
        judge_resp = _make_judge_response()
        factory = _mock_agent_factory(judge_resp)

        skill_a = _make_skill(slug="skill-a")
        skill_b = _make_skill(slug="skill-b")
        scenarios = skill_a.eval_spec.scenarios

        service = ComparativeEvalService(
            runner=runner,
            prompt_registry=_mock_prompt_registry(),
            agent_factory=factory,
            model_id="test-model",
            behavioral_eval_repo=repo,
        )

        await service.compare(skill_a, skill_b, scenarios)

        # The agent's .run() was called with the user message
        agent = factory.return_value
        call_args = agent.run.call_args[0][0]
        parsed = json.loads(call_args)
        assert "output_x" in parsed
        assert "output_y" in parsed
        # Must NOT contain skill identifiers
        assert "skill_a" not in call_args.lower()
        assert "skill_b" not in call_args.lower()

    async def test_randomisation_of_assignment(self) -> None:
        """Over many runs, assignment of skills to X/Y should not be deterministic."""
        runner = _mock_runner()
        repo = _mock_repo()
        judge_response = _make_judge_response(preference="X", confidence=0.9)

        skill_a = _make_skill(slug="skill-a", content="CONTENT_A")
        skill_b = _make_skill(slug="skill-b", content="CONTENT_B")

        # Run many single-scenario comparisons to check randomisation
        scenarios = [EvalScenario(description="Test", input_context="ctx", success_criteria="pass")]

        a_is_x_count = 0
        runs = 40

        for _ in range(runs):
            factory_local = _mock_agent_factory(judge_response)
            service = ComparativeEvalService(
                runner=runner,
                prompt_registry=_mock_prompt_registry(),
                agent_factory=factory_local,
                model_id="test-model",
                behavioral_eval_repo=repo,
            )
            # Check which content was called first (X position)
            await service.compare(skill_a, skill_b, scenarios)
            first_call_content = runner.run.call_args_list[-2][0][0]
            if first_call_content == "CONTENT_A":
                a_is_x_count += 1

        # With 40 runs, probability of all same assignment is ~2^-40
        assert 0 < a_is_x_count < runs, "Assignment should be randomised"

    async def test_low_confidence_forces_tie(self) -> None:
        """Confidence below threshold forces preference to 'tie'."""
        runner = _mock_runner()
        repo = _mock_repo()
        # Judge says X wins but confidence is only 0.3
        judge_resp = _make_judge_response(preference="X", confidence=0.3)
        factory = _mock_agent_factory(judge_resp)

        skill_a = _make_skill(slug="skill-a")
        skill_b = _make_skill(slug="skill-b")
        scenarios = skill_a.eval_spec.scenarios

        service = ComparativeEvalService(
            runner=runner,
            prompt_registry=_mock_prompt_registry(),
            agent_factory=factory,
            model_id="test-model",
            behavioral_eval_repo=repo,
            confidence_threshold=0.60,
        )

        result = await service.compare(skill_a, skill_b, scenarios)

        assert len(result.per_scenario) == 1
        assert result.per_scenario[0].winner == "tie"
        assert result.overall_winner == "tie"

    async def test_winner_mapped_back_from_xy_to_ab(self) -> None:
        """X/Y preference is correctly mapped back to a/b."""
        runner = _mock_runner()
        repo = _mock_repo()

        # Force assignment: patch random.choice to return True (a_is_x = True)
        judge_resp = _make_judge_response(preference="Y", confidence=0.9)
        factory = _mock_agent_factory(judge_resp)

        skill_a = _make_skill(slug="skill-a")
        skill_b = _make_skill(slug="skill-b")
        scenarios = skill_a.eval_spec.scenarios

        service = ComparativeEvalService(
            runner=runner,
            prompt_registry=_mock_prompt_registry(),
            agent_factory=factory,
            model_id="test-model",
            behavioral_eval_repo=repo,
        )

        # Fix randomisation: a_is_x = True means Y = b, so preference Y -> winner b
        with patch("loom.services.comparative_eval.random.choice", return_value=True):
            result = await service.compare(skill_a, skill_b, scenarios)

        assert result.per_scenario[0].winner == "b"

        # Now fix: a_is_x = False means Y = a, so preference Y -> winner a
        with patch("loom.services.comparative_eval.random.choice", return_value=False):
            result = await service.compare(skill_a, skill_b, scenarios)

        assert result.per_scenario[0].winner == "a"

    async def test_results_persisted(self) -> None:
        """Results are persisted via BehavioralEvalRepo.create_comparative_result()."""
        runner = _mock_runner()
        repo = _mock_repo()
        judge_resp = _make_judge_response()
        factory = _mock_agent_factory(judge_resp)

        skill_a = _make_skill(slug="skill-a")
        skill_b = _make_skill(slug="skill-b")
        scenarios = skill_a.eval_spec.scenarios

        service = ComparativeEvalService(
            runner=runner,
            prompt_registry=_mock_prompt_registry(),
            agent_factory=factory,
            model_id="test-model",
            behavioral_eval_repo=repo,
        )

        await service.compare(skill_a, skill_b, scenarios)

        repo.create_comparative_result.assert_called_once()
        call_kwargs = repo.create_comparative_result.call_args[1]
        assert call_kwargs["skill_a_id"] == skill_a.id
        assert call_kwargs["skill_b_id"] == skill_b.id
        assert call_kwargs["judge_model_id"] == "test-model"

    async def test_multiple_scenarios_produce_multiple_results(self) -> None:
        """Each scenario produces a separate ComparativeResult."""
        runner = _mock_runner()
        repo = _mock_repo()
        judge_resp = _make_judge_response()
        factory = _mock_agent_factory(judge_resp)

        two_scenarios = [
            EvalScenario(description="S1", input_context="c1", success_criteria="p1"),
            EvalScenario(description="S2", input_context="c2", success_criteria="p2"),
        ]
        skill_a = _make_skill(slug="skill-a")
        skill_b = _make_skill(slug="skill-b")

        service = ComparativeEvalService(
            runner=runner,
            prompt_registry=_mock_prompt_registry(),
            agent_factory=factory,
            model_id="test-model",
            behavioral_eval_repo=repo,
        )

        result = await service.compare(skill_a, skill_b, two_scenarios)

        assert len(result.per_scenario) == 2
        assert repo.create_comparative_result.call_count == 2
        assert runner.run.call_count == 4  # 2 scenarios x 2 skills

    async def test_overall_winner_by_majority(self) -> None:
        """Overall winner determined by majority across scenarios."""
        runner = _mock_runner()
        repo = _mock_repo()

        # Scenario 1: A wins (X wins, a_is_x=True)
        # Scenario 2: B wins (Y wins, a_is_x=True)
        # Scenario 3: A wins
        responses = [
            _make_judge_response(preference="X", confidence=0.9),
            _make_judge_response(preference="Y", confidence=0.9),
            _make_judge_response(preference="X", confidence=0.9),
        ]
        call_idx = 0

        def make_factory(resp: str) -> MagicMock:
            agent = MagicMock()
            result_obj = MagicMock()
            result_obj.output = resp
            agent.run = AsyncMock(return_value=result_obj)
            return agent

        def factory_side_effect(system_prompt: str) -> MagicMock:
            nonlocal call_idx
            agent = make_factory(responses[call_idx])
            call_idx += 1
            return agent

        factory = MagicMock(side_effect=factory_side_effect)

        three_scenarios = [
            EvalScenario(description=f"S{i}", input_context=f"c{i}", success_criteria=f"p{i}")
            for i in range(3)
        ]
        skill_a = _make_skill(slug="skill-a")
        skill_b = _make_skill(slug="skill-b")

        service = ComparativeEvalService(
            runner=runner,
            prompt_registry=_mock_prompt_registry(),
            agent_factory=factory,
            model_id="test-model",
            behavioral_eval_repo=repo,
        )

        # Fix assignment so a_is_x is always True for predictable mapping
        with patch("loom.services.comparative_eval.random.choice", return_value=True):
            result = await service.compare(skill_a, skill_b, three_scenarios)

        # A wins 2, B wins 1 -> overall A
        assert result.win_count_a == 2
        assert result.win_count_b == 1
        assert result.overall_winner == "a"
