"""Application settings loaded from loom.yaml with env var overrides."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5434
    name: str = "loom"
    user: str = "loom"
    password: str = "loom"
    url: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.url:
            self.url = f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class EmbeddingConfig(BaseModel):
    provider: Literal["openai", "openrouter"] = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    api_key: str = ""
    base_url: str | None = None


class LLMConfig(BaseModel):
    provider: Literal["openai", "openrouter"] = "openrouter"
    model: str = "google/gemini-3-flash-preview"
    api_key: str = ""
    base_url: str | None = None


class MCPTransportConfig(BaseModel):
    type: Literal["stdio", "sse", "streamable-http"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8080


class MCPConfig(BaseModel):
    transports: list[MCPTransportConfig] = [MCPTransportConfig()]


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6380
    url: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.url:
            self.url = f"redis://{self.host}:{self.port}"


class PipelineConfig(BaseModel):
    """Configuration for the quality assessment pipeline."""

    pass_threshold: float = 0.50
    promotion_threshold: float = 0.70
    safety_floor: float = 0.60
    runs_per_dimension: int = 3
    low_confidence_spread: float = 0.25
    sandbox_timeout_seconds: int = 30
    sandbox_memory_mb: int = 256
    sandbox_image: str = "loom-eval-sandbox:latest"
    max_content_length: int = 50_000
    max_steps: int = 50
    max_dependencies: int = 15

    # M4: Behavioral evaluation
    behavioral_runs_per_scenario: int = 3
    behavioral_pass_threshold: float = 0.50
    behavioral_floor_for_promotion: float = 0.60
    runner_model: str | None = None  # defaults to llm.model
    judge_model: str | None = None  # defaults to llm.model

    # M4: Comparative evaluation
    comparison_confidence_threshold: float = 0.60

    # M4: Amendment triage
    amendment_semantic_threshold_high: float = 0.95
    amendment_semantic_threshold_low: float = 0.70

    # M4: Usage signals
    usage_failure_rate_trigger: float = 0.30
    usage_success_rate_drop_trigger: float = 0.20
    staleness_window_days: int = 90

    # M4: Continuous re-evaluation
    reeval_sample_percent: float = 0.20
    reeval_drift_threshold: float = 0.15
    model_drift_threshold: float = 0.10

    # M4: Abuse prevention
    submission_rate_limit_unverified: int = 5
    submission_rate_limit_verified: int = 20
    duplicate_similarity_reject: float = 0.95
    duplicate_similarity_warn: float = 0.85


class YamlSettingsSource(PydanticBaseSettingsSource):
    """Load settings from loom.yaml if it exists."""

    def get_field_value(self, field: Any, field_name: str) -> Any:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        yaml_path = Path("loom.yaml")
        if yaml_path.exists():
            with open(yaml_path) as f:
                return yaml.safe_load(f) or {}
        return {}


class LoomSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LOOM_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database: DatabaseConfig = DatabaseConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    llm: LLMConfig = LLMConfig()
    mcp: MCPConfig = MCPConfig()
    api: APIConfig = APIConfig()
    redis: RedisConfig = RedisConfig()
    pipeline: PipelineConfig = PipelineConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls),
        )
