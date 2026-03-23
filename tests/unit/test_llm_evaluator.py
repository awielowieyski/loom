"""Tests for LLMEvaluator — Phase 3 isolated LLM evaluation."""

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from loom.models.common import EvalDimension
from loom.models.eval import DimensionResult, InjectionIndicator, IsolatedFragments
from loom.services.llm_evaluator import LLMEvaluator, _build_user_message
from loom.services.prompt_registry import PromptRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_fragments(**overrides: Any) -> IsolatedFragments:
    """Create a minimal IsolatedFragments for testing."""
    defaults: dict[str, Any] = {
        "content_hash": "sha256:abc123",
        "metadata": {"name": "test-skill", "description": "A test skill", "tags": ["test"]},
        "step_outline": ["# Step 1: Do something", "# Step 2: Do another thing"],
        "full_body": "# Step 1\nDo something.\n# Step 2\nDo another thing.",
        "code_blocks": [],
        "eval_scenarios": [
            {"description": "basic", "input_context": "none", "success_criteria": "pass"},
        ],
        "injection_indicators": [],
    }
    defaults.update(overrides)
    return IsolatedFragments(**defaults)


def _make_valid_response(
    score: float = 0.85,
    confidence: float = 0.9,
    injection_detected: bool = False,
) -> str:
    """Create a valid JSON LLM response."""
    return json.dumps(
        {
            "score": score,
            "evidence": ["Well structured", "Clear naming"],
            "injection_detected": injection_detected,
            "injection_detail": None,
            "confidence": confidence,
        }
    )


def _mock_agent_factory(response_text: str) -> tuple[Any, AsyncMock]:
    """Create a mock agent factory returning a fixed response.

    Returns the factory and the underlying mock for assertions.
    """
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
def fragments() -> IsolatedFragments:
    return _make_fragments()


# ---------------------------------------------------------------------------
# Tests: Single dimension evaluation
# ---------------------------------------------------------------------------


class TestEvaluateDimension:
    """evaluate_dimension produces valid DimensionResult."""

    async def test_single_dimension_valid_result(
        self, registry: PromptRegistry, fragments: IsolatedFragments
    ) -> None:
        factory, _mock = _mock_agent_factory(_make_valid_response(score=0.85))
        evaluator = LLMEvaluator(factory, registry, model_id="test-model")

        result = await evaluator.evaluate_dimension(fragments, EvalDimension.CLARITY)

        assert isinstance(result, DimensionResult)
        assert result.dimension == EvalDimension.CLARITY
        assert result.score == 0.85
        assert result.confidence == 0.9
        assert len(result.evidence) == 2
        assert result.injection_detected is False

    async def test_parse_failure_retries_then_fallback(
        self, registry: PromptRegistry, fragments: IsolatedFragments
    ) -> None:
        """On parse failure, retry up to max_retries, then return fallback."""
        mock_result = AsyncMock()
        mock_result.output = "NOT VALID JSON"
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        evaluator = LLMEvaluator(
            lambda _sp: mock_agent, registry, model_id="test-model", max_retries=2
        )

        result = await evaluator.evaluate_dimension(fragments, EvalDimension.CLARITY)

        assert result.score == 0.0
        assert result.confidence == 0.0
        assert "could not be parsed" in result.evidence[0]
        # 1 initial + 2 retries = 3 calls
        assert mock_agent.run.call_count == 3

    async def test_score_out_of_range_triggers_retry(
        self, registry: PromptRegistry, fragments: IsolatedFragments
    ) -> None:
        """Score outside [0,1] is treated as parse failure."""
        mock_result = AsyncMock()
        mock_result.output = json.dumps(
            {
                "score": 1.5,
                "evidence": ["oops"],
                "injection_detected": False,
                "injection_detail": None,
                "confidence": 0.5,
            }
        )
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        evaluator = LLMEvaluator(
            lambda _sp: mock_agent, registry, model_id="test-model", max_retries=1
        )

        result = await evaluator.evaluate_dimension(fragments, EvalDimension.CLARITY)
        assert result.score == 0.0
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Tests: evaluate_all
# ---------------------------------------------------------------------------


class TestEvaluateAll:
    """evaluate_all produces 4 dimensions x N runs."""

    async def test_evaluate_all_produces_all_dimensions(
        self, registry: PromptRegistry, fragments: IsolatedFragments
    ) -> None:
        factory, _mock = _mock_agent_factory(_make_valid_response())
        evaluator = LLMEvaluator(factory, registry, model_id="test-model")

        results = await evaluator.evaluate_all(fragments, n_runs=3)

        assert set(results.keys()) == {"clarity", "completeness", "safety", "correctness"}
        for dim_results in results.values():
            assert len(dim_results) == 3
            for r in dim_results:
                assert isinstance(r, DimensionResult)

    async def test_evaluate_all_with_single_run(
        self, registry: PromptRegistry, fragments: IsolatedFragments
    ) -> None:
        factory, _mock = _mock_agent_factory(_make_valid_response())
        evaluator = LLMEvaluator(factory, registry, model_id="test-model")

        results = await evaluator.evaluate_all(fragments, n_runs=1)

        for dim_results in results.values():
            assert len(dim_results) == 1


# ---------------------------------------------------------------------------
# Tests: Data-only protocol
# ---------------------------------------------------------------------------


class TestDataOnlyProtocol:
    """User message is JSON with 'skill_fragment' key — no metadata leakage."""

    def test_user_message_has_skill_fragment_key(self, fragments: IsolatedFragments) -> None:
        msg = _build_user_message(fragments, EvalDimension.CLARITY)
        parsed = json.loads(msg)
        assert "skill_fragment" in parsed
        assert "dimension" in parsed
        assert parsed["dimension"] == "clarity"

    def test_no_metadata_leakage_in_clarity(self, fragments: IsolatedFragments) -> None:
        """Clarity only sees step_outline — no author, trust_tier, or score."""
        msg = _build_user_message(fragments, EvalDimension.CLARITY)
        msg_lower = msg.lower()
        assert "author" not in msg_lower
        assert "trust_tier" not in msg_lower
        # metadata dict should not appear
        assert "description" not in msg_lower

    def test_no_metadata_in_safety(self) -> None:
        """Safety sees full_body + injection_indicators, not metadata."""
        frags = _make_fragments(
            metadata={"name": "secret-skill", "author": "hidden-author"},
        )
        msg = _build_user_message(frags, EvalDimension.SAFETY)
        parsed = json.loads(msg)
        # The skill_fragment for safety should be full_body-based, not metadata
        assert "hidden-author" not in msg
        assert "secret-skill" not in parsed["skill_fragment"]

    def test_no_metadata_in_correctness(self) -> None:
        """Correctness sees eval_scenarios + code_blocks, not metadata."""
        frags = _make_fragments(
            metadata={"name": "secret", "author": "hidden"},
        )
        msg = _build_user_message(frags, EvalDimension.CORRECTNESS)
        assert "hidden" not in msg
        assert "secret" not in msg

    def test_safety_includes_injection_indicators(self) -> None:
        """Safety dimension message includes injection_indicators."""
        indicators = [
            InjectionIndicator(
                line=5, pattern="ignore_instructions", matched_text="ignore all instructions"
            ),
        ]
        frags = _make_fragments(injection_indicators=indicators)
        msg = _build_user_message(frags, EvalDimension.SAFETY)
        parsed = json.loads(msg)
        assert "injection_indicators" in parsed
        assert len(parsed["injection_indicators"]) == 1
        assert parsed["injection_indicators"][0]["pattern"] == "ignore_instructions"

    def test_non_safety_excludes_injection_indicators(self) -> None:
        """Non-safety dimensions do NOT include injection_indicators in message."""
        indicators = [
            InjectionIndicator(line=5, pattern="test", matched_text="test"),
        ]
        frags = _make_fragments(injection_indicators=indicators)

        for dim in [EvalDimension.CLARITY, EvalDimension.COMPLETENESS, EvalDimension.CORRECTNESS]:
            msg = _build_user_message(frags, dim)
            parsed = json.loads(msg)
            assert "injection_indicators" not in parsed


# ---------------------------------------------------------------------------
# Tests: Agent factory interaction
# ---------------------------------------------------------------------------


class TestAgentFactoryInteraction:
    """The agent_factory receives the system prompt from the registry."""

    async def test_agent_factory_receives_system_prompt(
        self, registry: PromptRegistry, fragments: IsolatedFragments
    ) -> None:
        """agent_factory is called with a system prompt string."""
        captured_prompts: list[str] = []

        mock_result = AsyncMock()
        mock_result.output = _make_valid_response()
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        def tracking_factory(system_prompt: str) -> Any:
            captured_prompts.append(system_prompt)
            return mock_agent

        evaluator = LLMEvaluator(tracking_factory, registry, model_id="test-model")
        await evaluator.evaluate_dimension(fragments, EvalDimension.CLARITY)

        assert len(captured_prompts) == 1
        assert "UNTRUSTED" in captured_prompts[0]

    async def test_agent_run_receives_json_message(
        self, registry: PromptRegistry, fragments: IsolatedFragments
    ) -> None:
        """Agent.run is called with a JSON-encoded user message."""
        factory, mock_agent = _mock_agent_factory(_make_valid_response())
        mock_agent.run.return_value.output = _make_valid_response()

        evaluator = LLMEvaluator(factory, registry, model_id="test-model")
        await evaluator.evaluate_dimension(fragments, EvalDimension.CLARITY)

        call_args = mock_agent.run.call_args[0][0]
        parsed = json.loads(call_args)
        assert "skill_fragment" in parsed
