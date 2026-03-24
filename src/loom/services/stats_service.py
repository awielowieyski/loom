"""StatsService: registry health metrics and analytics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncpg


class StatsService:
    """Aggregates registry health metrics from skills, evals, and usage data."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get_overview(self) -> dict[str, Any]:
        """Return high-level registry health overview."""
        # Skill counts by trust tier
        tier_rows = await self._conn.fetch(
            """
            SELECT trust_tier, COUNT(*) AS cnt
            FROM skills
            WHERE deprecated_at IS NULL
            GROUP BY trust_tier
            """
        )
        skill_counts: dict[str, int] = {
            "experimental": 0,
            "community": 0,
            "verified": 0,
        }
        for row in tier_rows:
            skill_counts[row["trust_tier"]] = row["cnt"]

        # Capability count
        cap_row = await self._conn.fetchval("SELECT COUNT(*) FROM capabilities")

        # Behavioral eval coverage: skills with behavioral_score / total active
        total_skills = sum(skill_counts.values())
        behavioral_count = await self._conn.fetchval(
            """
            SELECT COUNT(*) FROM skills
            WHERE deprecated_at IS NULL AND behavioral_score IS NOT NULL
            """
        )
        behavioral_eval_coverage = behavioral_count / total_skills if total_skills > 0 else 0.0

        # Stale: no eval in 30 days
        stale_count = await self._conn.fetchval(
            """
            SELECT COUNT(*) FROM skills
            WHERE deprecated_at IS NULL
              AND (last_eval_at IS NULL OR last_eval_at < NOW() - INTERVAL '30 days')
            """
        )

        # Deprecated count
        deprecated_count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM skills WHERE deprecated_at IS NOT NULL"
        )

        # Total resolutions from usage_aggregates
        res_7d = await self._conn.fetchval(
            """
            SELECT COALESCE(SUM(success_count + partial_count + failure_count), 0)
            FROM usage_aggregates WHERE window_type = '7d'
            """
        )
        res_30d = await self._conn.fetchval(
            """
            SELECT COALESCE(SUM(success_count + partial_count + failure_count), 0)
            FROM usage_aggregates WHERE window_type = '30d'
            """
        )

        return {
            "skill_counts": skill_counts,
            "capability_count": cap_row,
            "behavioral_eval_coverage": round(behavioral_eval_coverage, 4),
            "stale_count": stale_count,
            "deprecated_count": deprecated_count,
            "total_resolutions_7d": res_7d,
            "total_resolutions_30d": res_30d,
        }

    async def get_eval_trends(
        self,
        category: str | None = None,
        weeks: int = 12,
    ) -> dict[str, Any]:
        """Return eval score distribution grouped by week."""
        category_filter = ""
        params: list[object] = [weeks]

        if category:
            category_filter = """
                AND ej.skill_id IN (
                    SELECT s.id FROM skills s
                    JOIN categories c ON s.category_id = c.id
                    WHERE c.slug = $2
                )
            """
            params.append(category)

        rows = await self._conn.fetch(
            f"""
            SELECT
                date_trunc('week', ej.completed_at) AS week,
                percentile_cont(0.25) WITHIN GROUP (ORDER BY ej.composite_score) AS p25,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY ej.composite_score) AS p50,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY ej.composite_score) AS p75,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY ej.behavioral_score)
                    FILTER (WHERE ej.behavioral_score IS NOT NULL) AS behavioral_p50,
                COUNT(*) AS eval_count
            FROM eval_jobs ej
            WHERE ej.status = 'completed'
              AND ej.completed_at >= NOW() - ($1 || ' weeks')::INTERVAL
              {category_filter}
            GROUP BY date_trunc('week', ej.completed_at)
            ORDER BY week
            """,
            *params,
        )

        windows = []
        for row in rows:
            windows.append(
                {
                    "week": row["week"].isoformat() if row["week"] else None,
                    "p25": round(row["p25"], 4) if row["p25"] is not None else None,
                    "p50": round(row["p50"], 4) if row["p50"] is not None else None,
                    "p75": round(row["p75"], 4) if row["p75"] is not None else None,
                    "behavioral_p50": (
                        round(row["behavioral_p50"], 4)
                        if row["behavioral_p50"] is not None
                        else None
                    ),
                    "eval_count": row["eval_count"],
                }
            )

        return {"weeks_requested": weeks, "category": category, "windows": windows}

    async def get_usage_heatmap(
        self,
        period_type: str = "week",
        periods: int = 12,
    ) -> dict[str, Any]:
        """Return usage heatmap: categories x time periods."""
        trunc = "week" if period_type == "week" else "month"

        rows = await self._conn.fetch(
            f"""
            SELECT
                c.slug AS category,
                date_trunc($1, ur.created_at) AS period,
                COUNT(*) AS resolution_count
            FROM usage_reports ur
            JOIN skills s ON ur.skill_id = s.id
            JOIN categories c ON s.category_id = c.id
            WHERE ur.created_at >= NOW() - ($2 || ' {trunc}s')::INTERVAL
            GROUP BY c.slug, date_trunc($1, ur.created_at)
            ORDER BY c.slug, period
            """,
            trunc,
            periods,
        )

        # Build category list, period list, and data matrix
        categories_set: dict[str, int] = {}
        periods_set: dict[str, int] = {}
        data: dict[tuple[str, str], int] = {}

        for row in rows:
            cat = row["category"]
            period_key = row["period"].isoformat() if row["period"] else ""
            if cat not in categories_set:
                categories_set[cat] = len(categories_set)
            if period_key not in periods_set:
                periods_set[period_key] = len(periods_set)
            data[(cat, period_key)] = row["resolution_count"]

        categories_list = list(categories_set.keys())
        periods_list = list(periods_set.keys())

        # Build matrix: rows=categories, columns=periods
        matrix: list[list[int]] = []
        for cat in categories_list:
            row_data = [data.get((cat, p), 0) for p in periods_list]
            matrix.append(row_data)

        return {
            "period_type": period_type,
            "categories": categories_list,
            "periods": periods_list,
            "data": matrix,
        }
