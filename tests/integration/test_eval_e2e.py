"""End-to-end test for the M2 eval pipeline with REAL LLM calls.

This test makes actual API calls to OpenRouter (12 calls: 4 dimensions x 3 runs).
It is marked with @pytest.mark.e2e so it does not run in CI.
Requires LOOM_LLM__API_KEY or the api_key in loom.yaml/.env to be set.
"""

from __future__ import annotations

import pytest
from pydantic_ai import Agent

from loom.models.common import EvalDimension
from loom.models.eval import DimensionResult
from loom.providers.llm import create_llm_model
from loom.services.content_isolator import isolate as isolate_content
from loom.services.eval_pipeline import EvalPipelineService
from loom.services.llm_evaluator import LLMEvaluator
from loom.services.prompt_registry import PromptRegistry
from loom.services.score_aggregator import ScoreAggregator
from loom.services.static_analyser import StaticAnalyser
from loom.settings import LoomSettings
from tests.helpers import make_test_skill


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_real_llm_eval_e2e() -> None:
    """Full pipeline with REAL LLM calls via OpenRouter.

    Makes 12 API calls (4 dimensions x 3 runs) and validates the complete
    evaluation result. This test is slow (~30-60s) and requires a valid API key.
    """
    # Step 1: Load settings
    settings = LoomSettings()

    # Step 2: Skip if no API key
    if not settings.llm.api_key:
        pytest.skip("No LLM API key configured — set LOOM_LLM__API_KEY or configure loom.yaml")

    # Step 3: Create real services
    static_analyser = StaticAnalyser()
    score_aggregator = ScoreAggregator()
    prompt_registry = PromptRegistry()

    # Step 4: Create real LLM model
    llm_model = create_llm_model(settings.llm)

    # Step 5: Create real agent factory
    def agent_factory(system_prompt: str) -> Agent[None, str]:
        return Agent(llm_model, system_prompt=system_prompt, output_type=str)

    # Step 6: Create real LLM evaluator
    llm_evaluator = LLMEvaluator(
        agent_factory=agent_factory,
        prompt_registry=prompt_registry,
        model_id=settings.llm.model,
        max_retries=2,
    )

    # Step 7: Content isolator (already imported as isolate_content)

    # Step 8: Build pipeline with all real services, no sandbox
    pipeline = EvalPipelineService(
        static_analyser=static_analyser,
        content_isolator=isolate_content,
        llm_evaluator=llm_evaluator,
        score_aggregator=score_aggregator,
        sandbox_runner=None,
    )

    # Step 9: Create a well-formed skill
    skill = make_test_skill()

    # Step 10: Run the pipeline (REAL LLM calls)
    print("\n" + "=" * 70)
    print(f"Running real LLM eval pipeline with model: {settings.llm.model}")
    print(f"Provider: {settings.llm.provider} | Base URL: {settings.llm.base_url}")
    print("Expected: 4 dimensions x 3 runs = 12 LLM API calls")
    print("=" * 70)

    result, structural, raw_dims = await pipeline.evaluate(skill)

    # --- Print results for manual inspection ---
    print("\n" + "-" * 70)
    print("STRUCTURAL REPORT")
    print(f"  passed: {structural.passed}")
    print(f"  errors: {structural.errors}")
    print(f"  warnings: {structural.warnings}")
    print(f"  content_hash: {structural.content_hash[:40]}...")
    print(f"  complexity_score: {structural.complexity_score}")

    print("\nDIMENSION RESULTS")
    for dim, runs in raw_dims.items():
        scores = [r.score for r in runs]
        confidences = [r.confidence for r in runs]
        injections = [r.injection_detected for r in runs]
        print(f"\n  {dim.value}:")
        print(f"    scores:      {scores}")
        print(f"    confidences: {confidences}")
        print(f"    injections:  {injections}")
        for i, run in enumerate(runs):
            print(
                f"    run {i} evidence: {run.evidence[:2]}{'...' if len(run.evidence) > 2 else ''}"
            )

    print("\nAGGREGATED RESULT")
    print(f"  passed:             {result.passed}")
    print(f"  composite_score:    {result.composite_score:.4f}")
    print(f"  dimension_scores:   {result.dimension_scores}")
    print(f"  dimension_conf:     {result.dimension_confidence}")
    print(f"  overall_confidence: {result.overall_confidence:.4f}")
    print(f"  injection_flagged:  {result.injection_flagged}")
    print(f"  content_hash:       {result.content_hash[:40]}...")
    print(f"  evaluator_version:  {result.evaluator_version}")
    print("-" * 70)

    # Step 11: Assertions
    assert result is not None, "Result should not be None"
    assert result.content_hash.startswith(
        "sha256:"
    ), f"Expected sha256: prefix, got {result.content_hash[:10]}"
    assert (
        0.0 <= result.composite_score <= 1.0
    ), f"Composite score {result.composite_score} not in [0, 1]"
    assert result.evaluator_version, "Evaluator version should be set"
    assert structural.passed, f"Structural report should pass, errors: {structural.errors}"
    assert len(raw_dims) == 4, f"Expected 4 dimensions, got {len(raw_dims)}"

    for dim in EvalDimension:
        assert dim in raw_dims, f"Missing dimension: {dim.value}"
        runs = raw_dims[dim]
        assert len(runs) == 3, f"Expected 3 runs for {dim.value}, got {len(runs)}"
        for run in runs:
            assert isinstance(run, DimensionResult)
            assert 0.0 <= run.score <= 1.0, f"Score {run.score} out of range for {dim.value}"
            assert (
                0.0 <= run.confidence <= 1.0
            ), f"Confidence {run.confidence} out of range for {dim.value}"

    print("\nAll assertions passed!")
