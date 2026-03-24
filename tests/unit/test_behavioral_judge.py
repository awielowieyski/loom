"""Tests for BehavioralJudge — assesses Runner output via Judge LLM."""

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from loom.models.behavioral import JudgeScore, RunnerOutput
from loom.models.common import EvalScenario, QualityDimension
from loom.services.behavioral_judge import BehavioralJudge
from loom.services.prompt_registry import PromptRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_runner_output(**overrides: Any) -> RunnerOutput:
    defaults = {
        "actions_taken": ["Read input", "Processed data"],
        "output": "Result: processed",
        "artifacts": ["output.txt"],
        "notes": None,
    }
    defaults.update(overrides)
    return RunnerOutput(**defaults)


def _make_scenario(**overrides: Any) -> EvalScenario:
    defaults = {
        "description": "Test scenario",
        "input_context": "User wants data processed",
        "success_criteria": "Data is processed correctly",
    }
    defaults.update(overrides)
    return EvalScenario(**defaults)


def _make_valid_judge_response(
    outcome_quality: float = 0.85,
    completeness: float = 0.80,
    efficiency: float = 0.90,
    injection_detected: bool = False,
) -> str:
    return json.dumps(
        {
            "outcome_quality": outcome_quality,
            "completeness": completeness,
            "efficiency": efficiency,
            "evidence": "Output meets criteria well",
            "confidence": 0.85,
            "injection_detected": injection_detected,
        }
    )


def _mock_agent_factory(response_text: str) -> tuple[Any, AsyncMock]:
    mock_result = AsyncMock()
    mock_result.output = response_text

    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=mock_result)

    def factory(system_prompt: str) -> Any:
        return mock_agent

    return factory, mock_agent


@pytest.fixture
def registry() -> PromptRegistry:
    return PromptRegistry()


@pytest.fixture
def runner_output() -> RunnerOutput:
    return _make_runner_output()


@pytest.fixture
def scenario() -> EvalScenario:
    return _make_scenario()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBehavioralJudge:
    """BehavioralJudge assessment tests."""

    async def test_judge_parses_valid_response(
        self,
        registry: PromptRegistry,
        runner_output: RunnerOutput,
        scenario: EvalScenario,
    ) -> None:
        """Valid LLM response is parsed into JudgeScore."""
        factory, _mock = _mock_agent_factory(_make_valid_judge_response())
        judge = BehavioralJudge(factory, registry, model_id="test-model")

        score, latency = await judge.judge(runner_output, scenario)

        assert isinstance(score, JudgeScore)
        assert score.outcome_quality == 0.85
        assert score.completeness == 0.80
        assert score.efficiency == 0.90
        assert score.confidence == 0.85
        assert score.injection_detected is False

    async def test_user_message_has_no_instructions_key(
        self,
        registry: PromptRegistry,
        runner_output: RunnerOutput,
        scenario: EvalScenario,
    ) -> None:
        """User message must NOT contain 'instructions' — judge never sees skill content."""
        factory, mock_agent = _mock_agent_factory(_make_valid_judge_response())
        judge = BehavioralJudge(factory, registry, model_id="test-model")

        await judge.judge(runner_output, scenario)

        call_args = mock_agent.run.call_args[0][0]
        parsed = json.loads(call_args)
        assert "instructions" not in parsed
        assert "skill_content" not in parsed
        assert "runner_output" in parsed
        assert "success_criteria" in parsed

    async def test_injection_detected_propagated(
        self,
        registry: PromptRegistry,
        runner_output: RunnerOutput,
        scenario: EvalScenario,
    ) -> None:
        """injection_detected from LLM response is preserved in JudgeScore."""
        factory, _mock = _mock_agent_factory(_make_valid_judge_response(injection_detected=True))
        judge = BehavioralJudge(factory, registry, model_id="test-model")

        score, _latency = await judge.judge(runner_output, scenario)

        assert score.injection_detected is True

    async def test_parse_failure_returns_fallback(
        self,
        registry: PromptRegistry,
        runner_output: RunnerOutput,
        scenario: EvalScenario,
    ) -> None:
        """On parse failure, returns JudgeScore with score=0.0, confidence=0.0."""
        mock_result = AsyncMock()
        mock_result.output = "NOT VALID JSON"
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        judge = BehavioralJudge(
            lambda _sp: mock_agent, registry, model_id="test-model", max_retries=1
        )

        score, _latency = await judge.judge(runner_output, scenario)

        assert score.outcome_quality == 0.0
        assert score.completeness == 0.0
        assert score.efficiency == 0.0
        assert score.confidence == 0.0
        # 1 initial + 1 retry = 2 calls
        assert mock_agent.run.call_count == 2

    async def test_latency_is_tracked(
        self,
        registry: PromptRegistry,
        runner_output: RunnerOutput,
        scenario: EvalScenario,
    ) -> None:
        """Latency is returned as second element of tuple."""
        factory, _mock = _mock_agent_factory(_make_valid_judge_response())
        judge = BehavioralJudge(factory, registry, model_id="test-model")

        _score, latency = await judge.judge(runner_output, scenario)

        assert latency is not None
        assert isinstance(latency, int)
        assert latency >= 0

    async def test_quality_dimensions_included_in_message(
        self,
        registry: PromptRegistry,
        runner_output: RunnerOutput,
        scenario: EvalScenario,
    ) -> None:
        """Quality dimensions are passed in the user message when provided."""
        dims = [
            QualityDimension(name="accuracy", description="How accurate"),
            QualityDimension(name="readability", description="How readable"),
        ]
        factory, mock_agent = _mock_agent_factory(_make_valid_judge_response())
        judge = BehavioralJudge(factory, registry, model_id="test-model")

        await judge.judge(runner_output, scenario, quality_dimensions=dims)

        call_args = mock_agent.run.call_args[0][0]
        parsed = json.loads(call_args)
        assert "quality_dimensions" in parsed
        assert len(parsed["quality_dimensions"]) == 2
        assert parsed["quality_dimensions"][0]["name"] == "accuracy"

    async def test_no_skill_content_leakage(
        self,
        registry: PromptRegistry,
        scenario: EvalScenario,
    ) -> None:
        """Even if RunnerOutput contains skill-like content, no 'instructions' key exists."""
        output_with_skill_ref = _make_runner_output(
            output="Following the skill instructions, I did X",
            notes="The skill told me to do Y",
        )
        factory, mock_agent = _mock_agent_factory(_make_valid_judge_response())
        judge = BehavioralJudge(factory, registry, model_id="test-model")

        await judge.judge(output_with_skill_ref, scenario)

        call_args = mock_agent.run.call_args[0][0]
        parsed = json.loads(call_args)
        # The runner_output may reference skills, but the MESSAGE structure
        # must not have an "instructions" key at the top level
        assert "instructions" not in parsed
        assert "skill_content" not in parsed
