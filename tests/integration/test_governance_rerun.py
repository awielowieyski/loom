"""Integration tests for governance rerun control-plane actions."""

import uuid

import asyncpg
import pytest

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.category import CategoryCreate
from loom.models.common import EvalScenario, EvalSpec
from loom.models.skill import SkillCreate
from loom.services.eval import EvalService
from loom.services.governance_service import GovernanceService
from loom.services.registry import RegistryService


@pytest.fixture
async def registry(db_conn: asyncpg.Connection) -> RegistryService:
    return RegistryService(
        skill_repo=SkillRepo(db_conn),
        category_repo=CategoryRepo(db_conn),
        eval_service=EvalService(),
    )


@pytest.fixture
async def setup_skill(
    db_conn: asyncpg.Connection,
    test_author_id: uuid.UUID,
) -> str:
    await CategoryRepo(db_conn).create(CategoryCreate(slug="external-tools", name="External Tools"))
    registry = RegistryService(
        skill_repo=SkillRepo(db_conn),
        category_repo=CategoryRepo(db_conn),
        eval_service=EvalService(),
    )
    skill = await registry.create_skill(
        SkillCreate(
            slug=f"rerun-skill-{uuid.uuid4().hex[:8]}",
            name="External Video Search",
            description="Use a hosted API to search YouTube videos.",
            content=(
                "Sign up at https://aisa.one and get an API key.\n"
                "Add credits (pay-as-you-go).\n"
                "Set AISA_API_KEY before running the skill.\n"
                "Use the AISA YouTube search API for results.\n"
            ),
            category_slug="external-tools",
            version="1.0.0",
            source_uri="https://aisa.one/docs/youtube-search",
            eval_spec=EvalSpec(
                scenarios=[
                    EvalScenario(
                        description="basic",
                        input_context="search videos",
                        success_criteria="returns results",
                    )
                ]
            ),
        ),
        author_id=test_author_id,
    )
    return str(skill.id)


@pytest.mark.asyncio
async def test_request_rerun_canonicalize_executes_immediately(
    db_conn: asyncpg.Connection,
    setup_skill: str,
) -> None:
    service = GovernanceService(db_conn)
    result = await service.request_rerun(
        skill_id=setup_skill,
        request_mode="canonicalize",
        note="Refresh service metadata",
    )

    assert result["success"] is True
    assert result["request"]["status"] == "completed"
    assert result["request"]["result_summary"]["service_count"] == 1
    dep_row = await db_conn.fetchrow(
        """
        SELECT s.service_key
        FROM skill_service_dependencies d
        JOIN external_services s ON s.id = d.service_id
        JOIN skills sk ON sk.current_version_id = d.skill_version_id
        WHERE sk.id::text = $1
        """,
        setup_skill,
    )
    assert dep_row is not None
    assert dep_row["service_key"] == "aisa.one"


@pytest.mark.asyncio
async def test_request_rerun_evaluate_is_queued(
    db_conn: asyncpg.Connection,
    setup_skill: str,
) -> None:
    service = GovernanceService(db_conn)
    result = await service.request_rerun(
        skill_id=setup_skill,
        request_mode="evaluate",
        note="Re-evaluate published revision",
    )

    assert result["success"] is True
    assert result["request"]["status"] == "pending"
    row = await db_conn.fetchrow(
        """
        SELECT request_mode, status
        FROM pipeline_run_requests
        WHERE skill_id::text = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        setup_skill,
    )
    assert row is not None
    assert row["request_mode"] == "evaluate"
    assert row["status"] == "pending"
