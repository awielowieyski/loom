"""Pipeline orchestrator — coordinates all assessment phases in sequence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from loom.models.common import EvalDimension
from loom.models.skill import SkillCreate

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


def _skill_to_skill_create(skill: Skill) -> SkillCreate:
    """Convert a Skill (DB record) to SkillCreate for static analysis."""
    return SkillCreate(
        slug=skill.slug,
        name=skill.name,
        description=skill.description,
        content=skill.content,
        category_slug="",  # Not needed for static analysis
        version=skill.version,
        tags=skill.tags,
        scope=skill.scope,
        trust_tier=skill.trust_tier,
        cost_profile=skill.cost_profile,
        cost_drivers=skill.cost_drivers,
        estimated_duration=skill.estimated_duration,
        dependencies=skill.dependencies,
        eval_spec=skill.eval_spec,
        extends=skill.extends,
    )


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
        self, skill: Skill
    ) -> tuple[EvalResult, StructuralReport, dict[EvalDimension, list[DimensionResult]]]:
        """Run the full evaluation pipeline on a skill.

        Short-circuits on structural failure (skips LLM evaluation).

        Args:
            skill: The skill to evaluate.

        Returns:
            Tuple of (EvalResult, StructuralReport, raw dimension runs).
            Raw dimension runs are empty dict on structural failure.
        """
        # Convert Skill -> SkillCreate for static analysis.
        skill_create = _skill_to_skill_create(skill)

        # Phase 1: Static analysis.
        structural: StructuralReport = self._static_analyser.analyse(skill_create)
        if not structural.passed:
            result = self._score_aggregator.aggregate(
                structural=structural,
                dimensions={},
            )
            return result, structural, {}

        # Phase 2: Content isolation.
        fragments = self._content_isolator(skill, structural)

        # Phase 3: LLM evaluation.
        raw_dimensions = await self._llm_evaluator.evaluate_all(fragments)
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
