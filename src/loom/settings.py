"""Application settings loaded from loom.yaml with env var overrides."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://loom:loom@localhost:5432/loom"


class EmbeddingConfig(BaseModel):
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536


class LLMConfig(BaseModel):
    provider: str = "openrouter"
    model: str = "google/gemini-3-flash"


class MCPTransportConfig(BaseModel):
    type: str = "stdio"
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
            YamlSettingsSource(settings_cls),
        )
