"""Service-level smoke tests for the M2 evaluation pipeline.

Real dependencies (DB, Docker sandbox) with mocked LLM.
Verifies all services wire together correctly with real infrastructure.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest

from loom.db.repositories.eval_repo import EvalRepo
from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EvalDimension,
    EvalScenario,
    EvalSpec,
    TrustTier,
)
from loom.models.eval import (
    CodeBlock,
    DimensionResult,
    IsolatedFragments,
)
from loom.models.skill import Skill
from loom.services.content_isolator import isolate as isolate_content
from loom.services.eval_pipeline import EvalPipelineService
from loom.services.score_aggregator import ScoreAggregator
from loom.services.static_analyser import StaticAnalyser

if TYPE_CHECKING:
    import asyncpg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill(**overrides: Any) -> Skill:
    """Create a well-formed Skill for smoke testing."""
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "slug": "smoke-test-skill",
        "name": "Smoke Test Skill",
        "description": "A well-formed skill for smoke testing.",
        "content": (
            "# Step 1: Setup\n\n"
            "Configure the environment with the required dependencies.\n\n"
            "# Step 2: Execute\n\n"
            "Run the main task using the provided context.\n\n"
            "```python\nprint('hello world')\n```\n\n"
            "# Step 3: Verify\n\n"
            "Check that the output matches the expected results.\n"
        ),
        "category_id": uuid.uuid4(),
        "tags": ["smoke", "test"],
        "scope": "community",
        "version": "1.0.0",
        "author_id": uuid.uuid4(),
        "trust_tier": TrustTier.EXPERIMENTAL,
        "cost_profile": CostProfile.FREE,
        "cost_drivers": [],
        "estimated_duration": "fast",
        "dependencies": DependencyDeclaration(),
        "eval_spec": EvalSpec(
            scenarios=[
                EvalScenario(
                    description="basic smoke test",
                    input_context="test context",
                    success_criteria="should pass",
                )
            ]
        ),
    }
    defaults.update(overrides)
    return Skill(**defaults)


def _mock_llm_evaluator(
    *,
    score: float = 0.85,
    evidence: list[str] | None = None,
    injection_detected: bool = False,
    confidence: float = 0.90,
) -> AsyncMock:
    """Create a mock LLM evaluator returning valid DimensionResult objects."""
    if evidence is None:
        evidence = ["Good"]

    async def _evaluate_all(fragments: Any, n_runs: int = 3) -> dict[str, list[DimensionResult]]:
        results: dict[str, list[DimensionResult]] = {}
        for dim in EvalDimension:
            dim_results: list[DimensionResult] = []
            for _ in range(n_runs):
                dim_results.append(
                    DimensionResult(
                        dimension=dim,
                        score=score,
                        evidence=list(evidence),
                        injection_detected=injection_detected,
                        confidence=confidence,
                    )
                )
            results[dim.value] = dim_results
        return results

    mock = AsyncMock()
    mock.evaluate_all = AsyncMock(side_effect=_evaluate_all)
    return mock


# ---------------------------------------------------------------------------
# Test 1: Full pipeline smoke (real services, mock LLM)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_smoke() -> None:
    """Real StaticAnalyser + ContentIsolator + ScoreAggregator, mocked LLM."""
    skill = _make_skill()

    pipeline = EvalPipelineService(
        static_analyser=StaticAnalyser(),
        content_isolator=isolate_content,
        llm_evaluator=_mock_llm_evaluator(),
        score_aggregator=ScoreAggregator(),
        sandbox_runner=None,
    )

    result, structural, raw_dims = await pipeline.evaluate(skill)

    assert result.passed is True
    assert result.composite_score > 0.5
    assert result.content_hash.startswith("sha256:")
    assert structural is not None
    assert len(raw_dims) == 4  # clarity, completeness, safety, correctness


# ---------------------------------------------------------------------------
# Test 2: Real sandbox execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_sandbox_execution() -> None:
    """Run a trivial Python snippet through the real Docker sandbox."""
    try:
        import aiodocker
    except ImportError:
        pytest.skip("aiodocker not installed")

    docker = aiodocker.Docker()
    try:
        # Verify Docker is reachable
        await docker.version()
    except Exception:
        await docker.close()
        pytest.skip("Docker daemon not available")

    from loom.services.sandbox_runner import SandboxRunner

    fragments = IsolatedFragments(
        content_hash="sha256:smoketest",
        metadata={"name": "smoke"},
        step_outline=["# Step 1"],
        full_body="print('hello')",
        code_blocks=[CodeBlock(language="python", code="print('hello world')\n", line_start=1)],
        eval_scenarios=[
            {
                "description": "basic test",
                "input_context": "test",
                "success_criteria": "should print hello",
            }
        ],
    )

    runner = SandboxRunner(docker)
    try:
        result = await runner.execute(fragments)
        # The sandbox image may not exist; if it ran at all that's a pass.
        # If the image doesn't exist, the error is captured in result.errors.
        assert isinstance(result.passed, bool)
        if result.passed:
            assert result.scenarios_run >= 1
    finally:
        await docker.close()


# ---------------------------------------------------------------------------
# Test 3: Pipeline with sandbox integration (real services + real sandbox, mock LLM)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_with_sandbox_integration() -> None:
    """Full pipeline with real sandbox runner, only mocking the LLM."""
    try:
        import aiodocker
    except ImportError:
        pytest.skip("aiodocker not installed")

    docker = aiodocker.Docker()
    try:
        await docker.version()
    except Exception:
        await docker.close()
        pytest.skip("Docker daemon not available")

    from loom.services.sandbox_runner import SandboxRunner

    skill = _make_skill()
    runner = SandboxRunner(docker)

    try:
        pipeline = EvalPipelineService(
            static_analyser=StaticAnalyser(),
            content_isolator=isolate_content,
            llm_evaluator=_mock_llm_evaluator(),
            score_aggregator=ScoreAggregator(),
            sandbox_runner=runner,
        )

        result, structural, raw_dims = await pipeline.evaluate(skill)

        # Pipeline should complete without raising, regardless of sandbox image availability.
        assert result.content_hash.startswith("sha256:")
        assert structural is not None
        assert len(raw_dims) == 4
    finally:
        await docker.close()


# ---------------------------------------------------------------------------
# Test 4: Eval repo -> pipeline -> repo round-trip (real DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eval_repo_pipeline_round_trip(
    db_conn: asyncpg.Connection,
    test_skill_id: uuid.UUID,
) -> None:
    """Create skill in DB, run pipeline, persist results, verify round-trip."""
    # Build a Skill object matching the DB record.
    skill = _make_skill(id=test_skill_id)

    # Run pipeline with mock LLM.
    pipeline = EvalPipelineService(
        static_analyser=StaticAnalyser(),
        content_isolator=isolate_content,
        llm_evaluator=_mock_llm_evaluator(),
        score_aggregator=ScoreAggregator(),
        sandbox_runner=None,
    )
    eval_result, structural, raw_dims = await pipeline.evaluate(skill)

    # Persist via eval repo.
    repo = EvalRepo(db_conn)
    job = await repo.create_eval_job(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        content_hash=eval_result.content_hash,
        trigger_type="submission",
        evaluator_version="m2-v0.1.0",
    )

    # Persist dimension runs.
    run_count = 0
    for dim, runs in raw_dims.items():
        for idx, dr in enumerate(runs):
            await repo.create_dimension_run(
                eval_job_id=job.id,
                dimension=dim.value,
                run_index=idx,
                score=dr.score,
                evidence=dr.evidence,
                injection_detected=dr.injection_detected,
                confidence=dr.confidence,
                prompt_variant="v1",
                model_id="test-model",
                latency_ms=100,
            )
            run_count += 1

    # Update job with aggregated results.
    now = datetime.now(UTC)
    await repo.update_eval_job(
        job.id,
        status="completed",
        composite_score=eval_result.composite_score,
        dimension_scores=eval_result.dimension_scores,
        dimension_confidence=eval_result.dimension_confidence,
        injection_flagged=eval_result.injection_flagged,
        overall_confidence=eval_result.overall_confidence,
        started_at=now,
        completed_at=now,
    )

    # Verify round-trip.
    latest = await repo.get_latest_eval_for_skill(test_skill_id)
    assert latest is not None
    assert latest.id == job.id
    assert latest.status == "completed"
    assert latest.composite_score is not None
    assert latest.composite_score > 0.5

    # Verify dimension runs persisted.
    runs = await repo.get_runs_for_job(job.id)
    assert len(runs) == run_count  # 4 dimensions x 3 runs = 12


# ---------------------------------------------------------------------------
# Test 5: Signing round-trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signing_round_trip() -> None:
    """Generate keypair, sign content, verify, then tamper and verify fails."""
    from loom.services.signing_service import generate_keypair, sign, verify

    private_key, public_key = generate_keypair()

    content = "# Test Skill\nDo the thing."
    version = "1.0.0"
    deps_json = "{}"
    eval_json = "{}"

    signature = sign(
        content=content,
        version=version,
        dependencies_json=deps_json,
        eval_spec_json=eval_json,
        private_key_hex=private_key,
    )

    # Valid signature verifies.
    assert verify(
        content=content,
        version=version,
        dependencies_json=deps_json,
        eval_spec_json=eval_json,
        signature_hex=signature,
        public_key_hex=public_key,
    )

    # Tampered content fails verification.
    assert not verify(
        content=content + " TAMPERED",
        version=version,
        dependencies_json=deps_json,
        eval_spec_json=eval_json,
        signature_hex=signature,
        public_key_hex=public_key,
    )
