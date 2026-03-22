from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    MCPServerDependency,
    PrivacyImpact,
    TrustRequirements,
    TrustTier,
)


def test_trust_tier_ordering() -> None:
    assert TrustTier.EXPERIMENTAL.rank < TrustTier.COMMUNITY.rank
    assert TrustTier.COMMUNITY.rank < TrustTier.VERIFIED.rank


def test_trust_tier_meets_floor() -> None:
    assert TrustTier.VERIFIED.meets_floor(TrustTier.COMMUNITY)
    assert TrustTier.COMMUNITY.meets_floor(TrustTier.COMMUNITY)
    assert not TrustTier.EXPERIMENTAL.meets_floor(TrustTier.COMMUNITY)


def test_cost_profile_within_budget() -> None:
    assert CostProfile.FREE.within_budget(CostProfile.LOW)
    assert CostProfile.LOW.within_budget(CostProfile.LOW)
    assert not CostProfile.HIGH.within_budget(CostProfile.LOW)


def test_privacy_impact_defaults() -> None:
    pi = PrivacyImpact()
    assert pi.external_data_sharing is False
    assert pi.input_logging == "unknown"
    assert pi.data_retention == "unknown"


def test_dependency_declaration_roundtrip() -> None:
    dep = DependencyDeclaration(
        mcp_servers=[
            MCPServerDependency(uri="filesystem", required=True, scopes=["read"]),
        ],
        trust_requirements=TrustRequirements(
            data_classification="none",
            network_access=False,
            privacy_impact=PrivacyImpact(external_data_sharing=False),
        ),
    )
    data = dep.model_dump()
    restored = DependencyDeclaration.model_validate(data)
    assert restored.mcp_servers[0].uri == "filesystem"
    assert restored.trust_requirements.privacy_impact.external_data_sharing is False
