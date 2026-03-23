"""Integration tests for capability CRUD, resolution, and extends merging.

Uses real database via the db_conn fixture (transactional rollback).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from loom.db.repositories.capability_repo import CapabilityRepo
from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.extends.resolver import ExtendsResolver
from loom.models.capability import CapabilityStep
from loom.models.category import CategoryCreate
from loom.models.common import (
    DependencyDeclaration,
    EvalScenario,
    EvalSpec,
    MCPServerDependency,
    TrustRequirements,
)

if TYPE_CHECKING:
    import asyncpg


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def cap_fixture(
    db_conn: asyncpg.Connection,
    test_author_id: uuid.UUID,
) -> tuple[CapabilityRepo, SkillRepo, uuid.UUID, uuid.UUID]:
    """Return (cap_repo, skill_repo, category_id, author_id)."""
    cat_repo = CategoryRepo(db_conn)
    cat = await cat_repo.create(
        CategoryCreate(slug=f"cap-test-{uuid.uuid4().hex[:8]}", name="Cap Test")
    )
    return CapabilityRepo(db_conn), SkillRepo(db_conn), cat.id, test_author_id


# ---------------------------------------------------------------------------
# CRUD Round-Trip
# ---------------------------------------------------------------------------


class TestCapabilityCRUD:
    """Create, read, update a capability and verify version history."""

    async def test_create_get_update_versions(
        self,
        cap_fixture: tuple[CapabilityRepo, SkillRepo, uuid.UUID, uuid.UUID],
    ) -> None:
        cap_repo, _, cat_id, author_id = cap_fixture

        steps = [
            CapabilityStep(skill_ref="loom://step-a", role="Step A"),
            CapabilityStep(skill_ref="loom://step-b", role="Step B"),
        ]

        # Create
        cap = await cap_repo.create(
            slug="crud-test",
            name="CRUD Test",
            description="Integration CRUD test",
            category_id=cat_id,
            tags=["test"],
            version="1.0.0",
            author_id=author_id,
            steps=steps,
            preconditions=["Pre 1"],
            expected_outcome="Outcome",
            data_flow=[],
            dependencies=DependencyDeclaration(),
            eval_spec=EvalSpec(),
        )
        assert cap.slug == "crud-test"
        assert cap.version == "1.0.0"
        assert len(cap.steps) == 2

        # Get by slug
        fetched = await cap_repo.get_by_slug("crud-test")
        assert fetched is not None
        assert fetched.id == cap.id
        assert fetched.steps[0].skill_ref == "loom://step-a"

        # Update (version bump)
        updated_steps = steps + [
            CapabilityStep(skill_ref="loom://step-c", role="Step C"),
        ]
        updated = await cap_repo.update(
            cap.id,
            version="1.1.0",
            author_id=author_id,
            steps=updated_steps,
            description="Updated description",
            changelog="Added step C",
        )
        assert updated is not None
        assert updated.version == "1.1.0"
        assert len(updated.steps) == 3

        # Verify version history
        versions = await cap_repo.get_versions(cap.id)
        assert len(versions) == 2
        version_nums = [v.version for v in versions]
        assert "1.0.0" in version_nums
        assert "1.1.0" in version_nums


# ---------------------------------------------------------------------------
# Full Plan Resolution (with real skills in DB)
# ---------------------------------------------------------------------------


class TestFullPlanResolution:
    """Create skills in DB, create capability referencing them, resolve."""

    async def test_resolve_steps_contain_skill_content(
        self,
        cap_fixture: tuple[CapabilityRepo, SkillRepo, uuid.UUID, uuid.UUID],
    ) -> None:
        cap_repo, skill_repo, cat_id, author_id = cap_fixture

        # Create 3 skills in the database
        skill_slugs = ["plan-skill-a", "plan-skill-b", "plan-skill-c"]
        created_skills = {}
        for slug in skill_slugs:
            skill = await skill_repo.create(
                slug=slug,
                name=f"Skill {slug}",
                description=f"Test skill {slug}",
                content=f"# Instructions for {slug}\nDo {slug} things.",
                category_id=cat_id,
                tags=[],
                version="1.0.0",
                author_id=author_id,
                dependencies=DependencyDeclaration(),
                eval_spec=EvalSpec(
                    scenarios=[
                        EvalScenario(
                            description="basic",
                            input_context="test",
                            success_criteria="pass",
                        )
                    ]
                ),
            )
            created_skills[slug] = skill

        # Create capability referencing these skills
        steps = [
            CapabilityStep(skill_ref=f"loom://{slug}", role=f"Do {slug}") for slug in skill_slugs
        ]
        cap = await cap_repo.create(
            slug="plan-resolution-test",
            name="Plan Resolution Test",
            description="Tests full plan resolution",
            category_id=cat_id,
            tags=[],
            version="1.0.0",
            author_id=author_id,
            steps=steps,
        )

        # Resolve each step manually (mimicking what CapabilityDiscoveryService does)
        for step in cap.steps:
            _, slug, _ = ExtendsResolver().parse_extends_uri(step.skill_ref)
            resolved_skill = await skill_repo.get_by_slug(slug)
            assert resolved_skill is not None, f"Skill {slug} not found"
            assert resolved_skill.content, f"Skill {slug} has no content"
            assert slug in resolved_skill.content


# ---------------------------------------------------------------------------
# Dependency Aggregation
# ---------------------------------------------------------------------------


class TestDependencyAggregation:
    """Capability with steps requiring different MCP servers: deps aggregated correctly."""

    async def test_aggregate_dependencies_from_steps(
        self,
        cap_fixture: tuple[CapabilityRepo, SkillRepo, uuid.UUID, uuid.UUID],
    ) -> None:
        from loom.services.capability_registry import CapabilityRegistryService

        cap_repo, skill_repo, cat_id, author_id = cap_fixture

        # Create skills with different dependencies
        deps_a = DependencyDeclaration(
            mcp_servers=[MCPServerDependency(uri="filesystem", required=True)],
            trust_requirements=TrustRequirements(data_classification="none"),
        )
        deps_b = DependencyDeclaration(
            mcp_servers=[
                MCPServerDependency(uri="filesystem", required=True),
                MCPServerDependency(uri="git", required=True),
            ],
            trust_requirements=TrustRequirements(
                data_classification="internal",
                network_access=True,
            ),
        )

        steps = [
            CapabilityStep(skill_ref="loom://dep-skill-a", role="Skill A"),
            CapabilityStep(skill_ref="loom://dep-skill-b", role="Skill B"),
        ]

        # Use the static aggregation method
        aggregated = CapabilityRegistryService.aggregate_dependencies(steps, [deps_a, deps_b])

        # filesystem should be deduplicated, git should be present
        mcp_uris = [m.uri for m in aggregated.mcp_servers]
        assert "filesystem" in mcp_uris
        assert "git" in mcp_uris
        assert mcp_uris.count("filesystem") == 1  # deduplicated

        # Trust requirements: highest classification, network_access = any
        assert aggregated.trust_requirements.data_classification == "internal"
        assert aggregated.trust_requirements.network_access is True


# ---------------------------------------------------------------------------
# Extends Chain Merge
# ---------------------------------------------------------------------------


class TestExtendsChainMerge:
    """Create base and extension capability dicts, merge, verify."""

    def test_merge_appends_steps_preserves_base(self) -> None:
        resolver = ExtendsResolver()

        base = {
            "steps": [
                {"skill_ref": "loom://review-pr", "role": "Review PR"},
                {"skill_ref": "loom://review-security", "role": "Security review"},
            ],
            "preconditions": ["PR available"],
            "expected_outcome": "Code reviewed",
            "data_flow": [
                {
                    "from_step": "review-pr",
                    "to_step": "review-security",
                    "classification": "internal",
                }
            ],
            "source": "loom",
            "slug": "base-review",
        }

        extension = {
            "steps": [
                {"skill_ref": "loom://review-perf", "role": "Performance review"},
            ],
            "preconditions": ["Perf benchmarks available"],
            "expected_outcome": "Comprehensive review",
            "data_flow": [
                {
                    "from_step": "review-security",
                    "to_step": "review-perf",
                    "classification": "internal",
                }
            ],
            "source": "corp",
            "slug": "extended-review",
        }

        result = resolver.merge_capability_layers([base, extension])

        # Base steps preserved in order
        assert len(result.steps) == 3
        assert result.steps[0]["skill_ref"] == "loom://review-pr"
        assert result.steps[1]["skill_ref"] == "loom://review-security"

        # Extension step appended
        assert result.steps[2]["skill_ref"] == "loom://review-perf"

        # Preconditions merged
        assert "PR available" in result.preconditions
        assert "Perf benchmarks available" in result.preconditions

        # Expected outcome from extension
        assert result.expected_outcome == "Comprehensive review"

        # Data flow edges merged
        assert len(result.data_flow) == 2

        # Layer metadata tracked
        assert len(result.layers) == 2
        assert result.layers[0].source == "loom"
        assert result.layers[1].source == "corp"
