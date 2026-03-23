"""Pipeline orchestrator — coordinates all assessment phases in sequence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from loom.models.common import EvalDimension

if TYPE_CHECKING:
    from collections.abc import Callable

    from loom.models.eval import (
        DimensionResult,
        EvalResult,
        IsolatedFragments,
        SandboxResult,
        StructuralReport,
    )
    from loom.models.skill import Skill
    from loom.services.score_aggregator import ScoreAggregator
    from loom.services.static_analyser import StaticAnalyser


class LLMEvaluatorProtocol(Protocol):
    """Protocol for the LLM evaluator (Phase 3)."""

    async def evaluate_all(
        self,
        fragments: IsolatedFragments,
        n_runs: int = 3,
    ) -> dict[str, list[DimensionResult]]: ...


class SandboxRunnerProtocol(Protocol):
    """Protocol for the sandbox runner (Phase 4)."""

    async def execute(
        self,
        fragments: IsolatedFragments,
    ) -> SandboxResult: ...


def _str_keys_to_enum(
    results: dict[str, list[DimensionResult]],
) -> dict[EvalDimension, list[DimensionResult]]:
    """Convert string-keyed dimension results to EvalDimension-keyed."""
    return {EvalDimension(k): v for k, v in results.items()}


class EvalPipelineService:
    """Orchestrates the five-phase evaluation pipeline.

    Phases:
        1. Static analysis (StaticAnalyser)
        2. Content isolation (isolate_content)
        3. LLM evaluation (LLMEvaluator)
        4. Sandbox execution (SandboxRunner, optional)
        5. Score aggregation (ScoreAggregator)
    """

    def __init__(
        self,
        static_analyser: StaticAnalyser,
        content_isolator: Callable[..., IsolatedFragments],
        llm_evaluator: LLMEvaluatorProtocol,
        score_aggregator: ScoreAggregator,
        sandbox_runner: SandboxRunnerProtocol | None = None,
    ) -> None:
        self._static_analyser = static_analyser
        self._content_isolator = content_isolator
        self._llm_evaluator = llm_evaluator
        self._score_aggregator = score_aggregator
        self._sandbox_runner = sandbox_runner

    async def evaluate(
        self,
        skill: Skill,
        runs_per_dimension: int = 3,
    ) -> tuple[EvalResult, StructuralReport, dict[EvalDimension, list[DimensionResult]]]:
        """Run the full evaluation pipeline on a skill.

        Short-circuits on structural failure (skips LLM evaluation).

        Args:
            skill: The skill to evaluate.
            runs_per_dimension: Number of LLM evaluation runs per dimension.

        Returns:
            Tuple of (EvalResult, StructuralReport, raw dimension runs).
            Raw dimension runs are empty dict on structural failure.
        """
        # Phase 1: Static analysis (accepts Skill directly).
        structural: StructuralReport = self._static_analyser.analyse(skill)
        if not structural.passed:
            result = self._score_aggregator.aggregate(
                structural=structural,
                dimensions={},
            )
            return result, structural, {}

        # Phase 2: Content isolation.
        fragments = self._content_isolator(skill, structural)

        # Phase 3: LLM evaluation.
        raw_dimensions = await self._llm_evaluator.evaluate_all(
            fragments, n_runs=runs_per_dimension
        )
        dimensions = _str_keys_to_enum(raw_dimensions)

        # Phase 4: Sandbox execution (optional).
        sandbox: SandboxResult | None = None
        if self._sandbox_runner is not None:
            sandbox = await self._sandbox_runner.execute(fragments)

        # Phase 5: Score aggregation.
        result = self._score_aggregator.aggregate(
            structural=structural,
            dimensions=dimensions,
            sandbox=sandbox,
        )
        return result, structural, dimensions
