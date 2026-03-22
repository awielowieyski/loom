"""Application settings loaded from loom.yaml with env var overrides."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://loom:loom@localhost:5434/loom"


class EmbeddingConfig(BaseModel):
    provider: Literal["openai", "openrouter"] = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    api_key: str = ""
    base_url: str | None = None


class LLMConfig(BaseModel):
    provider: Literal["openai", "openrouter"] = "openrouter"
    model: str = "google/gemini-3-flash"
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
    )

    database: DatabaseConfig = DatabaseConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    llm: LLMConfig = LLMConfig()
    mcp: MCPConfig = MCPConfig()
    api: APIConfig = APIConfig()

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
