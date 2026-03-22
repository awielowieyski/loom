import uuid

from loom.models.common import CostProfile, DependencyDeclaration, EvalSpec, TrustTier
from loom.models.skill import Skill, SkillCreate


def test_skill_create_minimal() -> None:
    skill = SkillCreate(
        slug="test-skill",
        name="Test Skill",
        description="A test skill",
        content="# Test\nDo the thing.",
        category_slug="development/git",
        version="1.0.0",
    )
    assert skill.slug == "test-skill"
    assert skill.trust_tier == TrustTier.EXPERIMENTAL
    assert skill.cost_profile == CostProfile.FREE


def test_skill_create_full() -> None:
    skill = SkillCreate(
        slug="full-skill",
        name="Full Skill",
        description="A fully specified skill",
        content="# Full\nDo everything.",
        category_slug="development/git",
        version="1.0.0",
        tags=["git", "commits"],
        cost_profile=CostProfile.LOW,
        cost_drivers=["LLM API call"],
        estimated_duration="moderate",
        dependencies=DependencyDeclaration(),
        eval_spec=EvalSpec(),
        extends="loom://base-skill@1.0.0",
    )
    assert skill.tags == ["git", "commits"]
    assert skill.extends == "loom://base-skill@1.0.0"


def test_skill_model() -> None:
    skill = Skill(
        id=uuid.uuid4(),
        slug="test-skill",
        name="Test Skill",
        description="A test skill",
        content="# Test",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=TrustTier.EXPERIMENTAL,
        cost_profile=CostProfile.FREE,
        cost_drivers=[],
        estimated_duration="fast",
        dependencies={},
        eval_spec={},
    )
    assert skill.signature is None
    assert skill.extends is None
