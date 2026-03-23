"""Tests for ContentIsolator — Phase 2 fragment extraction."""

import uuid

from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EvalScenario,
    EvalSpec,
    Scope,
    TrustTier,
)
from loom.models.eval import InjectionIndicator, StructuralReport
from loom.models.skill import Skill
from loom.services.content_isolator import isolate, normalise_content


def _make_skill(
    content: str = "# Step 1\nDo the thing.\n\n## Step 2\nDo another thing.",
    **kwargs,
) -> Skill:
    defaults = dict(
        id=uuid.uuid4(),
        slug="test-skill",
        name="Test Skill",
        description="A test skill for isolation",
        content=content,
        category_id=uuid.uuid4(),
        tags=["testing", "example"],
        scope=Scope.COMMUNITY,
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=TrustTier.EXPERIMENTAL,
        cost_profile=CostProfile.FREE,
        cost_drivers=[],
        estimated_duration="fast",
        dependencies=DependencyDeclaration(),
        eval_spec=EvalSpec(),
    )
    defaults.update(kwargs)
    return Skill(**defaults)


def _make_report(
    content_hash: str = "sha256:abc123",
    injection_indicators: list[InjectionIndicator] | None = None,
) -> StructuralReport:
    return StructuralReport(
        passed=True,
        content_hash=content_hash,
        injection_indicators=injection_indicators or [],
    )


class TestContentHashForwarding:
    def test_content_hash_carried_forward(self) -> None:
        skill = _make_skill()
        report = _make_report(content_hash="sha256:deadbeef1234")
        fragments = isolate(skill, report)
        assert fragments.content_hash == "sha256:deadbeef1234"


class TestStepOutline:
    def test_step_outline_contains_only_headings(self) -> None:
        content = (
            "# Heading 1\nBody text here.\n\n## Heading 2\nMore body.\n\n### Sub heading\nDetails."
        )
        skill = _make_skill(content=content)
        fragments = isolate(skill, _make_report())

        assert fragments.step_outline == [
            "# Heading 1",
            "## Heading 2",
            "### Sub heading",
        ]

    def test_step_outline_excludes_body_text(self) -> None:
        content = "# Step 1\nThis is body text, not a heading.\nAnother line."
        skill = _make_skill(content=content)
        fragments = isolate(skill, _make_report())

        assert len(fragments.step_outline) == 1
        assert "body text" not in fragments.step_outline[0]

    def test_step_outline_empty_when_no_headings(self) -> None:
        content = "Just plain text with no headings."
        skill = _make_skill(content=content)
        fragments = isolate(skill, _make_report())
        assert fragments.step_outline == []


class TestFullBody:
    def test_full_body_present_and_complete(self) -> None:
        content = "# Step 1\nDo the thing.\n\n## Step 2\nDo another thing."
        skill = _make_skill(content=content)
        fragments = isolate(skill, _make_report())
        assert fragments.full_body == content

    def test_full_body_normalised(self) -> None:
        # Content with zero-width chars should be cleaned
        content = "Hello\u200bWorld\u200c!\ufeff"
        skill = _make_skill(content=content)
        fragments = isolate(skill, _make_report())
        assert fragments.full_body == "HelloWorld!"


class TestCodeBlocks:
    def test_code_blocks_extracted_with_language(self) -> None:
        content = (
            "# Setup\n\n```python\nprint('hello')\n```\n\nSome text.\n\n```bash\necho hi\n```\n"
        )
        skill = _make_skill(content=content)
        fragments = isolate(skill, _make_report())

        assert len(fragments.code_blocks) == 2
        assert fragments.code_blocks[0].language == "python"
        assert fragments.code_blocks[0].code == "print('hello')\n"
        assert fragments.code_blocks[1].language == "bash"
        assert fragments.code_blocks[1].code == "echo hi\n"

    def test_code_block_line_start(self) -> None:
        content = "Line 1\nLine 2\n```python\nx = 1\n```\n"
        skill = _make_skill(content=content)
        fragments = isolate(skill, _make_report())

        assert len(fragments.code_blocks) == 1
        # Opening fence is on line 3 (1-based)
        assert fragments.code_blocks[0].line_start == 3

    def test_code_block_without_language(self) -> None:
        content = "```\nplain code\n```\n"
        skill = _make_skill(content=content)
        fragments = isolate(skill, _make_report())

        assert len(fragments.code_blocks) == 1
        assert fragments.code_blocks[0].language == ""
        assert fragments.code_blocks[0].code == "plain code\n"

    def test_no_code_blocks(self) -> None:
        content = "# Just headings\nNo code here."
        skill = _make_skill(content=content)
        fragments = isolate(skill, _make_report())
        assert fragments.code_blocks == []


class TestInjectionIndicators:
    def test_injection_indicators_passed_through(self) -> None:
        indicators = [
            InjectionIndicator(
                line=5, pattern="ignore_instructions", matched_text="ignore previous instructions"
            ),
            InjectionIndicator(line=12, pattern="role_assignment", matched_text="system:"),
        ]
        skill = _make_skill()
        report = _make_report(injection_indicators=indicators)
        fragments = isolate(skill, report)

        assert len(fragments.injection_indicators) == 2
        assert fragments.injection_indicators[0].pattern == "ignore_instructions"
        assert fragments.injection_indicators[1].line == 12

    def test_empty_injection_indicators(self) -> None:
        skill = _make_skill()
        fragments = isolate(skill, _make_report())
        assert fragments.injection_indicators == []


class TestMetadata:
    def test_metadata_contains_expected_fields(self) -> None:
        skill = _make_skill(
            name="My Skill",
            description="Does great things",
            tags=["ai", "code"],
            cost_profile=CostProfile.LOW,
            estimated_duration="moderate",
            scope=Scope.CORPORATE,
        )
        fragments = isolate(skill, _make_report())
        meta = fragments.metadata

        assert meta["name"] == "My Skill"
        assert meta["description"] == "Does great things"
        assert meta["tags"] == ["ai", "code"]
        assert meta["cost_profile"] == "low"
        assert meta["estimated_duration"] == "moderate"
        assert meta["scope"] == "corporate"
        assert meta["dependency_count"] == 0

    def test_metadata_dependency_count(self) -> None:
        from loom.models.common import APIDependency, MCPServerDependency

        deps = DependencyDeclaration(
            mcp_servers=[MCPServerDependency(uri="https://example.com")],
            apis=[
                APIDependency(name="openai"),
                APIDependency(name="github"),
            ],
        )
        skill = _make_skill(dependencies=deps)
        fragments = isolate(skill, _make_report())
        assert fragments.metadata["dependency_count"] == 3


class TestEvalScenarios:
    def test_eval_scenarios_serialised(self) -> None:
        scenarios = [
            EvalScenario(
                description="Basic test",
                input_context="Given a repo",
                success_criteria="Returns commit message",
            )
        ]
        skill = _make_skill(eval_spec=EvalSpec(scenarios=scenarios))
        fragments = isolate(skill, _make_report())

        assert len(fragments.eval_scenarios) == 1
        assert fragments.eval_scenarios[0]["description"] == "Basic test"
        assert fragments.eval_scenarios[0]["input_context"] == "Given a repo"
        assert fragments.eval_scenarios[0]["success_criteria"] == "Returns commit message"

    def test_empty_eval_scenarios(self) -> None:
        skill = _make_skill()
        fragments = isolate(skill, _make_report())
        assert fragments.eval_scenarios == []


class TestUnicodeNormalisation:
    def test_strips_zero_width_space(self) -> None:
        assert normalise_content("a\u200bb") == "ab"

    def test_strips_zero_width_non_joiner(self) -> None:
        assert normalise_content("a\u200cb") == "ab"

    def test_strips_zero_width_joiner(self) -> None:
        assert normalise_content("a\u200db") == "ab"

    def test_strips_bom(self) -> None:
        assert normalise_content("\ufeffhello") == "hello"

    def test_strips_rtl_overrides(self) -> None:
        # U+202A (LRE), U+202B (RLE), U+202C (PDF), U+202D (LRO), U+202E (RLO)
        text = "a\u202ab\u202bc\u202cd\u202de\u202ef"
        assert normalise_content(text) == "abcdef"

    def test_strips_bidi_isolates(self) -> None:
        # U+2066 (LRI), U+2067 (RLI), U+2068 (FSI), U+2069 (PDI)
        text = "a\u2066b\u2067c\u2068d\u2069e"
        assert normalise_content(text) == "abcde"

    def test_nfc_normalisation(self) -> None:
        # e + combining acute accent -> e-acute (NFC form)
        text = "e\u0301"
        result = normalise_content(text)
        assert result == "\u00e9"

    def test_full_body_strips_zero_width_in_headings(self) -> None:
        content = "# He\u200bading\nBody text."
        skill = _make_skill(content=content)
        fragments = isolate(skill, _make_report())
        assert "\u200b" not in fragments.full_body
        assert "# Heading" in fragments.full_body
