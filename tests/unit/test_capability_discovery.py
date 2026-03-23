"""Tests for CapabilityDiscoveryService — Tasks 8 & 9."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.capability import Capability, CapabilityStep, CapabilitySummary, DataFlowEdge
from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    MCPServerDependency,
    TrustTier,
)
from loom.models.resolution import (
    ResolutionContext,
    ResolutionError,
    ResolvedCapability,
)
from loom.models.skill import Skill
from loom.services.capability_discovery import CapabilityDiscoveryService


def _make_capability_summary(
    slug: str,
    trust_tier: TrustTier = TrustTier.COMMUNITY,
    cost_profile: CostProfile = CostProfile.FREE,
    cap_id: uuid.UUID | None = None,
) -> CapabilitySummary:
    return CapabilitySummary(
        id=cap_id or uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        version="1.0.0",
        trust_tier=trust_tier,
        cost_profile=cost_profile,
        estimated_duration="slow",
        step_count=2,
    )


def _make_capability(
    slug: str,
    steps: list[CapabilityStep] | None = None,
    trust_tier: TrustTier = TrustTier.COMMUNITY,
    cost_profile: CostProfile = CostProfile.FREE,
    cap_id: uuid.UUID | None = None,
    data_flow: list[DataFlowEdge] | None = None,
) -> Capability:
    if steps is None:
        steps = [
            CapabilityStep(skill_ref="loom://skill-a", role="Step A"),
            CapabilityStep(skill_ref="loom://skill-b", role="Step B"),
        ]
    return Capability(
        id=cap_id or uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=trust_tier,
        steps=steps,
        preconditions=[],
        expected_outcome="",
        data_flow=data_flow or [],
        cost_profile=cost_profile,
        cost_drivers=[],
        estimated_duration="slow",
    )


def _make_skill(
    slug: str,
    trust_tier: TrustTier = TrustTier.COMMUNITY,
    cost_profile: CostProfile = CostProfile.FREE,
    content: str | None = None,
    dependencies: DependencyDeclaration | None = None,
) -> Skill:
    return Skill(
        id=uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        content=content or f"# {slug}\nDo the thing.",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=trust_tier,
        cost_profile=cost_profile,
        cost_drivers=[],
        estimated_duration="fast",
        dependencies=dependencies or DependencyDeclaration(),
    )


@pytest.fixture
def mock_embedder() -> MagicMock:
    embedder = MagicMock()
    embed_result = MagicMock()
    embed_result.embeddings = [[0.1] * 1536]
    embedder.embed_query = AsyncMock(return_value=embed_result)
    return embedder


@pytest.fixture
def mock_cap_repo() -> MagicMock:
    repo = MagicMock()
    repo.vector_search_summary = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_skill_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_slug = AsyncMock(return_value=None)
    return repo


# ---------------------------------------------------------------------------
# Task 8 tests
# ---------------------------------------------------------------------------


async def test_resolve_returns_resolved_capability(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """Resolve returns ResolvedCapability with embedded skill content per step."""
    cap_id = uuid.uuid4()
    summary = _make_capability_summary("deploy-pipeline", cap_id=cap_id)
    full_cap = _make_capability("deploy-pipeline", cap_id=cap_id)

    skill_a = _make_skill("skill-a", content="# Skill A\nBuild the artifact.")
    skill_b = _make_skill("skill-b", content="# Skill B\nDeploy the artifact.")

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cap)
    mock_skill_repo.get_by_slug = AsyncMock(
        side_effect=lambda slug, version=None: {
            "skill-a": skill_a,
            "skill-b": skill_b,
        }.get(slug)
    )

    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("deploy a pipeline")

    assert isinstance(result, ResolvedCapability)
    assert result.capability.slug == "deploy-pipeline"
    assert len(result.resolved_steps) == 2
    # Each step has full skill content
    assert result.resolved_steps[0].skill.content == "# Skill A\nBuild the artifact."
    assert result.resolved_steps[1].skill.content == "# Skill B\nDeploy the artifact."


async def test_resolve_with_trust_floor_filters_capabilities(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """Capabilities below trust floor are rejected."""
    exp_cap = _make_capability_summary("exp-cap", trust_tier=TrustTier.EXPERIMENTAL)
    ver_id = uuid.uuid4()
    ver_cap = _make_capability_summary("ver-cap", trust_tier=TrustTier.VERIFIED, cap_id=ver_id)
    full_ver = _make_capability("ver-cap", trust_tier=TrustTier.VERIFIED, cap_id=ver_id)

    skill_a = _make_skill("skill-a", trust_tier=TrustTier.VERIFIED)
    skill_b = _make_skill("skill-b", trust_tier=TrustTier.VERIFIED)

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[exp_cap, ver_cap])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_ver)
    mock_skill_repo.get_by_slug = AsyncMock(
        side_effect=lambda slug, version=None: {
            "skill-a": skill_a,
            "skill-b": skill_b,
        }.get(slug)
    )

    context = ResolutionContext(trust_floor=TrustTier.COMMUNITY)
    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("do something", context=context)

    assert isinstance(result, ResolvedCapability)
    assert result.capability.slug == "ver-cap"


async def test_resolve_effective_trust_from_step_skills(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """Effective trust tier is the minimum across all resolved step skills."""
    cap_id = uuid.uuid4()
    summary = _make_capability_summary("mixed-cap", trust_tier=TrustTier.VERIFIED, cap_id=cap_id)
    full_cap = _make_capability("mixed-cap", trust_tier=TrustTier.VERIFIED, cap_id=cap_id)

    skill_a = _make_skill("skill-a", trust_tier=TrustTier.VERIFIED)
    skill_b = _make_skill("skill-b", trust_tier=TrustTier.EXPERIMENTAL)

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cap)
    mock_skill_repo.get_by_slug = AsyncMock(
        side_effect=lambda slug, version=None: {
            "skill-a": skill_a,
            "skill-b": skill_b,
        }.get(slug)
    )

    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("mixed trust")

    assert isinstance(result, ResolvedCapability)
    # Effective trust should be experimental (the min)
    assert result.effective_trust_tier == TrustTier.EXPERIMENTAL


async def test_resolve_effective_trust_rejects_below_floor(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """If effective trust (from step skills) falls below trust floor, return error."""
    cap_id = uuid.uuid4()
    summary = _make_capability_summary("mixed-cap", trust_tier=TrustTier.VERIFIED, cap_id=cap_id)
    full_cap = _make_capability("mixed-cap", trust_tier=TrustTier.VERIFIED, cap_id=cap_id)

    skill_a = _make_skill("skill-a", trust_tier=TrustTier.VERIFIED)
    skill_b = _make_skill("skill-b", trust_tier=TrustTier.EXPERIMENTAL)

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cap)
    mock_skill_repo.get_by_slug = AsyncMock(
        side_effect=lambda slug, version=None: {
            "skill-a": skill_a,
            "skill-b": skill_b,
        }.get(slug)
    )

    context = ResolutionContext(trust_floor=TrustTier.COMMUNITY)
    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("mixed trust", context=context)

    assert isinstance(result, ResolutionError)
    assert "effective trust tier" in result.message


async def test_resolve_with_cost_budget_filters(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """Capabilities exceeding cost budget are penalised."""
    cheap_id = uuid.uuid4()
    expensive = _make_capability_summary("expensive", cost_profile=CostProfile.HIGH)
    cheap = _make_capability_summary("cheap", cost_profile=CostProfile.FREE, cap_id=cheap_id)
    full_cheap = _make_capability("cheap", cost_profile=CostProfile.FREE, cap_id=cheap_id)

    skill_a = _make_skill("skill-a")
    skill_b = _make_skill("skill-b")

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[expensive, cheap])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cheap)
    mock_skill_repo.get_by_slug = AsyncMock(
        side_effect=lambda slug, version=None: {
            "skill-a": skill_a,
            "skill-b": skill_b,
        }.get(slug)
    )

    context = ResolutionContext(cost_budget=CostProfile.LOW)
    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("find something cheap", context=context)

    assert isinstance(result, ResolvedCapability)
    assert result.capability.slug == "cheap"


async def test_search_returns_summaries(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """Search returns a list of CapabilitySummary."""
    summaries = [
        _make_capability_summary("cap-a"),
        _make_capability_summary("cap-b"),
    ]
    mock_cap_repo.vector_search_summary = AsyncMock(return_value=summaries)

    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.search("deploy")

    assert len(result) == 2
    assert result[0].slug == "cap-a"


async def test_resolve_no_candidates_returns_error(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """No match returns ResolutionError."""
    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[])

    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("nothing matches")

    assert isinstance(result, ResolutionError)
    assert result.error == "no_match"


# ---------------------------------------------------------------------------
# Task 9 tests — full plan resolution enhancement
# ---------------------------------------------------------------------------


async def test_resolved_steps_contain_full_skill_content(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """Each ResolvedStep contains the complete skill.content."""
    cap_id = uuid.uuid4()
    summary = _make_capability_summary("content-cap", cap_id=cap_id)
    full_cap = _make_capability("content-cap", cap_id=cap_id)

    skill_a = _make_skill("skill-a", content="Full content of skill A with instructions.")
    skill_b = _make_skill("skill-b", content="Full content of skill B with instructions.")

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cap)
    mock_skill_repo.get_by_slug = AsyncMock(
        side_effect=lambda slug, version=None: {
            "skill-a": skill_a,
            "skill-b": skill_b,
        }.get(slug)
    )

    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("full content")

    assert isinstance(result, ResolvedCapability)
    assert "Full content of skill A" in result.resolved_steps[0].skill.content
    assert "Full content of skill B" in result.resolved_steps[1].skill.content


async def test_optional_step_with_unmet_deps_marked_not_rejected(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """required=false steps with unmet deps are marked but resolution still succeeds."""
    cap_id = uuid.uuid4()
    steps = [
        CapabilityStep(skill_ref="loom://skill-a", role="Required step"),
        CapabilityStep(skill_ref="loom://skill-b", role="Optional step", required=False),
    ]
    summary = _make_capability_summary("opt-cap", cap_id=cap_id)
    full_cap = _make_capability("opt-cap", steps=steps, cap_id=cap_id)

    skill_a = _make_skill("skill-a")
    skill_b = _make_skill(
        "skill-b",
        dependencies=DependencyDeclaration(
            mcp_servers=[MCPServerDependency(uri="mcp://unavailable-server")]
        ),
    )

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cap)
    mock_skill_repo.get_by_slug = AsyncMock(
        side_effect=lambda slug, version=None: {
            "skill-a": skill_a,
            "skill-b": skill_b,
        }.get(slug)
    )

    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("optional deps")

    assert isinstance(result, ResolvedCapability)
    # Step 1 (optional) has missing deps but resolution succeeds
    assert result.resolved_steps[1].required is False
    assert "mcp://unavailable-server" in result.resolved_steps[1].dependencies_missing


async def test_required_step_with_unmet_deps_reported(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """required=true step with unmet deps: resolution succeeds but deps reported."""
    cap_id = uuid.uuid4()
    steps = [
        CapabilityStep(skill_ref="loom://skill-a", role="Required step"),
    ]
    summary = _make_capability_summary("req-cap", cap_id=cap_id)
    full_cap = _make_capability("req-cap", steps=steps, cap_id=cap_id)

    skill_a = _make_skill(
        "skill-a",
        dependencies=DependencyDeclaration(
            mcp_servers=[MCPServerDependency(uri="mcp://required-server")]
        ),
    )

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cap)
    mock_skill_repo.get_by_slug = AsyncMock(return_value=skill_a)

    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("required deps")

    assert isinstance(result, ResolvedCapability)
    assert "mcp://required-server" in result.all_dependencies_missing


async def test_trust_warnings_for_experimental_skills(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """Trust warnings are generated when experimental skills are present."""
    cap_id = uuid.uuid4()
    summary = _make_capability_summary("exp-cap", cap_id=cap_id)
    full_cap = _make_capability("exp-cap", cap_id=cap_id)

    skill_a = _make_skill("skill-a", trust_tier=TrustTier.VERIFIED)
    skill_b = _make_skill("skill-b", trust_tier=TrustTier.EXPERIMENTAL)

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cap)
    mock_skill_repo.get_by_slug = AsyncMock(
        side_effect=lambda slug, version=None: {
            "skill-a": skill_a,
            "skill-b": skill_b,
        }.get(slug)
    )

    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    # No trust floor, so experimental doesn't cause rejection
    result = await service.resolve("trust warnings")

    assert isinstance(result, ResolvedCapability)
    assert any("experimental" in w for w in result.trust_warnings)


async def test_external_data_flow_produces_safety_warning(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """External data flow edges produce safety warnings in selection_rationale."""
    cap_id = uuid.uuid4()
    data_flow = [
        DataFlowEdge(from_step="step-a", to_step="step-b", classification="external"),
    ]
    summary = _make_capability_summary("flow-cap", cap_id=cap_id)
    full_cap = _make_capability("flow-cap", cap_id=cap_id, data_flow=data_flow)

    skill_a = _make_skill("skill-a")
    skill_b = _make_skill("skill-b")

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cap)
    mock_skill_repo.get_by_slug = AsyncMock(
        side_effect=lambda slug, version=None: {
            "skill-a": skill_a,
            "skill-b": skill_b,
        }.get(slug)
    )

    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("data flow")

    assert isinstance(result, ResolvedCapability)
    assert any("untrusted" in r for r in result.selection_rationale)
    assert any("external" in r for r in result.selection_rationale)


async def test_corp_skill_ref_creates_placeholder(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """corp:// references produce placeholder Skill objects."""
    cap_id = uuid.uuid4()
    steps = [
        CapabilityStep(skill_ref="corp://internal-tool", role="Corp step"),
    ]
    summary = _make_capability_summary("corp-cap", cap_id=cap_id)
    full_cap = _make_capability("corp-cap", steps=steps, cap_id=cap_id)

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cap)

    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("corp skill")

    assert isinstance(result, ResolvedCapability)
    assert result.resolved_steps[0].skill.slug == "internal-tool"
    assert "Corporate skill not available" in result.resolved_steps[0].skill.content


async def test_dependency_satisfaction_with_available_tools(
    mock_cap_repo: MagicMock,
    mock_skill_repo: MagicMock,
    mock_embedder: MagicMock,
) -> None:
    """Per-step deps checked against context.available_tools."""
    cap_id = uuid.uuid4()
    steps = [CapabilityStep(skill_ref="loom://skill-a", role="Step A")]
    summary = _make_capability_summary("dep-cap", cap_id=cap_id)
    full_cap = _make_capability("dep-cap", steps=steps, cap_id=cap_id)

    skill_a = _make_skill(
        "skill-a",
        dependencies=DependencyDeclaration(
            mcp_servers=[
                MCPServerDependency(uri="mcp://available-server"),
                MCPServerDependency(uri="mcp://missing-server"),
            ]
        ),
    )

    mock_cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_cap_repo.get_by_id = AsyncMock(return_value=full_cap)
    mock_skill_repo.get_by_slug = AsyncMock(return_value=skill_a)

    context = ResolutionContext(available_tools=["mcp://available-server"])
    service = CapabilityDiscoveryService(
        capability_repo=mock_cap_repo,
        skill_repo=mock_skill_repo,
        embedder=mock_embedder,
    )
    result = await service.resolve("deps check", context=context)

    assert isinstance(result, ResolvedCapability)
    step = result.resolved_steps[0]
    assert "mcp://available-server" in step.dependencies_satisfied
    assert "mcp://missing-server" in step.dependencies_missing
    assert "mcp://available-server" in result.all_dependencies_satisfied
    assert "mcp://missing-server" in result.all_dependencies_missing
