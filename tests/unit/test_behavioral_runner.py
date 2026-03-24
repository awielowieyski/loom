"""Tests for BehavioralRunner — simulates skill execution via Runner LLM."""

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from loom.models.behavioral import RunnerOutput
from loom.models.common import EvalScenario
from loom.services.behavioral_runner import BehavioralRunner
from loom.services.prompt_registry import PromptRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_scenario(**overrides: Any) -> EvalScenario:
    defaults = {
        "description": "Test scenario",
        "input_context": "User wants to sort a list of numbers",
        "success_criteria": "Returns sorted list",
    }
    defaults.update(overrides)
    return EvalScenario(**defaults)


def _make_valid_runner_response() -> str:
    return json.dumps(
        {
            "actions_taken": ["Read the list", "Applied sort algorithm"],
            "output": "Sorted list: [1, 2, 3]",
            "artifacts": ["sorted_output.txt"],
            "notes": "Used quicksort",
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
def scenario() -> EvalScenario:
    return _make_scenario()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBehavioralRunner:
    """BehavioralRunner simulation tests."""

    async def test_runner_parses_valid_response(
        self, registry: PromptRegistry, scenario: EvalScenario
    ) -> None:
        """Valid LLM response is parsed into RunnerOutput."""
        factory, _mock = _mock_agent_factory(_make_valid_runner_response())
        runner = BehavioralRunner(factory, registry, model_id="test-model")

        output, latency = await runner.run("# Step 1\nDo something", scenario)

        assert isinstance(output, RunnerOutput)
        assert len(output.actions_taken) == 2
        assert "Sorted list" in output.output
        assert len(output.artifacts) == 1
        assert output.notes == "Used quicksort"

    async def test_user_message_contains_instructions_and_scenario(
        self, registry: PromptRegistry, scenario: EvalScenario
    ) -> None:
        """User message has 'instructions' and 'scenario' keys."""
        factory, mock_agent = _mock_agent_factory(_make_valid_runner_response())
        runner = BehavioralRunner(factory, registry, model_id="test-model")

        await runner.run("skill content here", scenario)

        call_args = mock_agent.run.call_args[0][0]
        parsed = json.loads(call_args)
        assert "instructions" in parsed
        assert "scenario" in parsed
        assert parsed["instructions"] == "skill content here"
        assert parsed["scenario"]["input_context"] == scenario.input_context
        assert parsed["scenario"]["success_criteria"] == scenario.success_criteria
        assert parsed["scenario"]["description"] == scenario.description

    async def test_system_prompt_from_registry(
        self, registry: PromptRegistry, scenario: EvalScenario
    ) -> None:
        """System prompt comes from PromptRegistry behavioral variant."""
        captured_prompts: list[str] = []

        mock_result = AsyncMock()
        mock_result.output = _make_valid_runner_response()
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        def tracking_factory(system_prompt: str) -> Any:
            captured_prompts.append(system_prompt)
            return mock_agent

        runner = BehavioralRunner(tracking_factory, registry, model_id="test-model")
        await runner.run("content", scenario)

        assert len(captured_prompts) == 1
        assert "UNTRUSTED" in captured_prompts[0]

    async def test_parse_failure_retries_then_fallback(
        self, registry: PromptRegistry, scenario: EvalScenario
    ) -> None:
        """On parse failure, retry up to max_retries, then return fallback."""
        mock_result = AsyncMock()
        mock_result.output = "NOT VALID JSON"
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        runner = BehavioralRunner(
            lambda _sp: mock_agent, registry, model_id="test-model", max_retries=2
        )

        output, latency = await runner.run("content", scenario)

        assert output.actions_taken == []
        assert output.output == ""
        assert output.artifacts == []
        # 1 initial + 2 retries = 3 calls
        assert mock_agent.run.call_count == 3

    async def test_latency_is_tracked(
        self, registry: PromptRegistry, scenario: EvalScenario
    ) -> None:
        """Latency is returned as second element of tuple."""
        factory, _mock = _mock_agent_factory(_make_valid_runner_response())
        runner = BehavioralRunner(factory, registry, model_id="test-model")

        _output, latency = await runner.run("content", scenario)

        assert latency is not None
        assert isinstance(latency, int)
        assert latency >= 0

    async def test_code_fences_stripped(
        self, registry: PromptRegistry, scenario: EvalScenario
    ) -> None:
        """Response wrapped in code fences is handled correctly."""
        fenced = "```json\n" + _make_valid_runner_response() + "\n```"
        factory, _mock = _mock_agent_factory(fenced)
        runner = BehavioralRunner(factory, registry, model_id="test-model")

        output, _latency = await runner.run("content", scenario)

        assert isinstance(output, RunnerOutput)
        assert len(output.actions_taken) == 2
