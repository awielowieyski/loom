"""EvalService: structural validation of skills (M1 stub, no LLM)."""

from pydantic import BaseModel

from loom.models.skill import SkillCreate

MIN_CONTENT_LENGTH = 10


class ValidationResult(BaseModel):
    passed: bool
    errors: list[str]
    warnings: list[str] = []


class EvalService:
    """Validates skill structure without calling any LLM."""

    def validate_structure(self, skill: SkillCreate) -> ValidationResult:
        """Check structural constraints and return a ValidationResult."""
        errors: list[str] = []
        warnings: list[str] = []

        # Content must be non-empty and at least MIN_CONTENT_LENGTH chars
        if not skill.content or len(skill.content) < MIN_CONTENT_LENGTH:
            errors.append(f"Skill content must be at least {MIN_CONTENT_LENGTH} characters long")

        # Must have at least one eval scenario
        if not skill.eval_spec.scenarios:
            errors.append("Skill eval_spec must contain at least 1 scenario")

        # Dependency structure: check MCP server URIs are non-empty
        for dep in skill.dependencies.mcp_servers:
            if not dep.uri:
                errors.append("MCP server dependency has empty URI")

        return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings)
