#!/usr/bin/env python3
"""Run evaluations in-process (no Redis/arq required).

Usage:
    uv run python scripts/run_eval.py --slug conventional-commit
    uv run python scripts/run_eval.py --unevaluated --limit 10
    uv run python scripts/run_eval.py --source awesome-cursorrules
    uv run python scripts/run_eval.py --all --limit 5

Requires LOOM_LLM__API_KEY in .env for the LLM evaluator.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve project root and add src/ to path so loom package is importable
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Loom skill evaluations in-process.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--slug", help="Evaluate a single skill by slug")
    group.add_argument(
        "--unevaluated",
        action="store_true",
        help="Evaluate skills that haven't been evaluated yet",
    )
    group.add_argument("--source", help="Evaluate skills matching a source_uri pattern")
    group.add_argument("--all", action="store_true", help="Evaluate all skills")

    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max number of skills to evaluate in batch mode (default: 50)",
    )
    parser.add_argument(
        "--runs-per-dimension",
        type=int,
        default=None,
        help="Override runs_per_dimension from settings",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    logger = logging.getLogger("run_eval")

    from loom.db.engine import create_pool
    from loom.db.repositories.skill_repo import SkillRepo
    from loom.services.eval_runner import _create_default_services, run_evaluation
    from loom.settings import LoomSettings

    settings = LoomSettings()
    runs_per_dimension = args.runs_per_dimension or settings.pipeline.runs_per_dimension

    # Build pipeline services once (shared across all evals)
    static_analyser, llm_evaluator, score_aggregator = _create_default_services(
        static_analyser=None,
        llm_evaluator=None,
        score_aggregator=None,
    )

    pool = await create_pool(settings.database.url)
    try:
        # Resolve which skills to evaluate
        skills: list = []
        async with pool.acquire() as conn:
            skill_repo = SkillRepo(conn)

            if args.slug:
                skill = await skill_repo.get_by_slug(args.slug)
                if skill is None:
                    logger.error("Skill with slug %r not found", args.slug)
                    sys.exit(1)
                skills = [skill]
            elif args.unevaluated:
                skills = await skill_repo.get_unevaluated(limit=args.limit)
            elif args.source:
                skills = await skill_repo.get_by_source_pattern(args.source, limit=args.limit)
            elif args.all:
                summaries = await skill_repo.list_all()
                # list_all returns summaries; we need full skills for eval
                for s in summaries[: args.limit]:
                    full = await skill_repo.get_by_id(s.id)
                    if full is not None:
                        skills.append(full)

        if not skills:
            logger.warning("No skills matched the filter — nothing to evaluate.")
            return

        logger.info("Evaluating %d skill(s)...", len(skills))

        passed_count = 0
        failed_count = 0
        error_count = 0

        for i, skill in enumerate(skills, 1):
            logger.info("[%d/%d] Evaluating %s ...", i, len(skills), skill.slug)
            try:
                result = await run_evaluation(
                    pool,
                    skill.id,
                    trigger="cli",
                    static_analyser=static_analyser,
                    llm_evaluator=llm_evaluator,
                    score_aggregator=score_aggregator,
                    runs_per_dimension=runs_per_dimension,
                )
                if "error" in result:
                    logger.error("  -> Error: %s", result["error"])
                    error_count += 1
                else:
                    status = "PASS" if result["passed"] else "FAIL"
                    logger.info(
                        "  -> %s  score=%.2f  job=%s",
                        status,
                        result["composite_score"],
                        result["job_id"],
                    )
                    if result["passed"]:
                        passed_count += 1
                    else:
                        failed_count += 1
            except Exception:
                logger.exception("  -> Exception evaluating %s", skill.slug)
                error_count += 1

        logger.info(
            "Done. %d passed, %d failed, %d errors out of %d total.",
            passed_count,
            failed_count,
            error_count,
            len(skills),
        )
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
