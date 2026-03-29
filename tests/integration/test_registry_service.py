"""Integration tests for RegistryService."""

import uuid

import asyncpg
import pytest

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.service_metadata_repo import ServiceMetadataRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.category import CategoryCreate
from loom.models.common import EvalScenario, EvalSpec
from loom.models.service_metadata import (
    PricingFactWrite,
    ServiceDependencyWrite,
    ServiceSetupRequirementWrite,
)
from loom.models.skill import SkillCreate
from loom.services.eval import EvalService
from loom.services.registry import RegistryService


@pytest.fixture
async def registry(db_conn: asyncpg.Connection) -> RegistryService:
    cat_repo = CategoryRepo(db_conn)
    skill_repo = SkillRepo(db_conn)
    eval_service = EvalService()
    return RegistryService(skill_repo=skill_repo, category_repo=cat_repo, eval_service=eval_service)


@pytest.fixture
async def setup(db_conn: asyncpg.Connection, test_author_id: uuid.UUID) -> uuid.UUID:
    """Create prerequisite category, return author_id."""
    await CategoryRepo(db_conn).create(CategoryCreate(slug="code-gen", name="Code Generation"))
    return test_author_id


async def _make_skill(**overrides: object) -> SkillCreate:
    defaults: dict[str, object] = {
        "slug": f"reg-skill-{uuid.uuid4().hex[:8]}",
        "name": "Registry Skill",
        "description": "A skill for registry tests",
        "content": "This is valid content for the registry skill that is long enough",
        "category_slug": "code-gen",
        "version": "1.0.0",
        "eval_spec": EvalSpec(
            scenarios=[EvalScenario(description="d", input_context="c", success_criteria="s")]
        ),
    }
    defaults.update(overrides)
    return SkillCreate(**defaults)  # type: ignore[arg-type]


async def test_create_skill_succeeds(registry: RegistryService, setup: uuid.UUID) -> None:
    author_id = setup
    data = await _make_skill()
    skill = await registry.create_skill(data, author_id=author_id)
    assert skill.id is not None
    assert skill.slug == data.slug
    assert skill.version == "1.0.0"


async def test_create_skill_fails_validation(registry: RegistryService, setup: uuid.UUID) -> None:
    author_id = setup
    data = await _make_skill(content="short")
    with pytest.raises(ValueError, match="content"):
        await registry.create_skill(data, author_id=author_id)


async def test_create_skill_fails_unknown_category(
    registry: RegistryService, setup: uuid.UUID
) -> None:
    author_id = setup
    data = await _make_skill(category_slug="no-such-category")
    with pytest.raises(ValueError, match="[Cc]ategory"):
        await registry.create_skill(data, author_id=author_id)


async def test_get_skill(registry: RegistryService, setup: uuid.UUID) -> None:
    author_id = setup
    data = await _make_skill()
    created = await registry.create_skill(data, author_id=author_id)

    fetched = await registry.get_skill(data.slug)
    assert fetched is not None
    assert fetched.id == created.id


async def test_list_skills(registry: RegistryService, setup: uuid.UUID) -> None:
    author_id = setup
    data = await _make_skill()
    await registry.create_skill(data, author_id=author_id)

    skills = await registry.list_skills()
    assert any(s.slug == data.slug for s in skills)


async def test_get_skill_includes_external_service_metadata(
    registry: RegistryService,
    db_conn: asyncpg.Connection,
    setup: uuid.UUID,
) -> None:
    author_id = setup
    data = await _make_skill(
        content=(
            "Use https://aisa.one/docs for YouTube search.\n"
            "Pricing: YouTube search costs ~$0.002.\n"
            "Sign up, add credits, and export AISA_API_KEY=your-key.\n"
        )
    )
    created = await registry.create_skill(data, author_id=author_id)
    assert created.current_version_id is not None

    service_repo = ServiceMetadataRepo(db_conn)
    await service_repo.replace_skill_version_metadata(
        skill_version_id=created.current_version_id,
        dependencies=[
            ServiceDependencyWrite(
                service_key="aisa.one",
                display_name="AISA",
                service_type="api",
                homepage_url="https://aisa.one",
                docs_url="https://aisa.one/docs",
                default_auth_methods=["api_key"],
                default_env_vars=["AISA_API_KEY"],
                pricing_summary={
                    "pricing_model": "usage_based",
                    "requires_paid_account": True,
                    "indicative_unit_cost_usd": 0.002,
                },
                evidence_summary={"source": "test"},
            )
        ],
        pricing_facts=[
            PricingFactWrite(
                fact_type="unit_cost",
                pricing_model="usage_based",
                operation_name="youtube_search",
                unit_name="request",
                unit_cost_usd=0.002,
                currency="USD",
                price_text_raw="YouTube search costs ~$0.002",
                source_uri="https://aisa.one/docs",
                evidence_snippet="YouTube search costs ~$0.002",
                confidence=0.8,
            )
        ],
        setup_requirements=[
            ServiceSetupRequirementWrite(
                service_key="aisa.one",
                requirement_type="env_var",
                key="AISA_API_KEY",
                value_hint="api_key",
                instructions="Set AISA_API_KEY before running the skill.",
                evidence_summary={"source": "test"},
            )
        ],
    )

    fetched = await registry.get_skill(data.slug)
    assert fetched is not None
    assert fetched.external_services
    assert fetched.external_services[0].service.service_key == "aisa.one"
    assert fetched.pricing
    assert fetched.pricing[0].unit_cost_usd == 0.002
    assert fetched.setup_requirements
    assert fetched.setup_requirements[0].key == "AISA_API_KEY"
    assert fetched.requires_paid_service is True
    assert fetched.requires_network is True
