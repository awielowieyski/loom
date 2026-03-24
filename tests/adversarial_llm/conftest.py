"""Shared fixtures for adversarial LLM evaluation tests.

These tests make real API calls to verify the security model works end-to-end.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pydantic_ai import Agent

from loom.providers.llm import create_llm_model
from loom.services.content_isolator import isolate as isolate_content
from loom.services.eval_pipeline import EvalPipelineService
from loom.services.llm_evaluator import LLMEvaluator
from loom.services.prompt_registry import PromptRegistry
from loom.services.score_aggregator import ScoreAggregator
from loom.services.static_analyser import StaticAnalyser
from loom.settings import LoomSettings
from tests.helpers import make_test_skill

if TYPE_CHECKING:
    from loom.models.skill import Skill


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "adversarial_llm: tests requiring real LLM API calls for adversarial evaluation",
    )


@pytest.fixture(scope="module")
def pipeline() -> EvalPipelineService:
    """Build a real EvalPipelineService with actual LLM calls."""
    settings = LoomSettings()
    if not settings.llm.api_key:
        pytest.skip("No LLM API key configured — set LOOM_LLM__API_KEY or configure loom.yaml")

    static_analyser = StaticAnalyser()
    score_aggregator = ScoreAggregator()
    prompt_registry = PromptRegistry()

    llm_model = create_llm_model(settings.llm)

    def agent_factory(system_prompt: str) -> Agent[None, str]:
        return Agent(llm_model, system_prompt=system_prompt, output_type=str)

    llm_evaluator = LLMEvaluator(
        agent_factory=agent_factory,
        prompt_registry=prompt_registry,
        model_id=settings.llm.model,
        max_retries=2,
    )

    return EvalPipelineService(
        static_analyser=static_analyser,
        content_isolator=isolate_content,
        llm_evaluator=llm_evaluator,
        score_aggregator=score_aggregator,
        sandbox_runner=None,
    )


@pytest.fixture()
def make_skill() -> Any:
    """Factory fixture that creates Skill objects with overridable content."""

    def _make(content: str, **overrides: Any) -> Skill:
        return make_test_skill(content=content, **overrides)

    return _make
