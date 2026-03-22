"""LLM provider factory."""

import os

from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from loom.settings import LLMConfig


def create_llm_model(config: LLMConfig) -> OpenRouterModel:
    """Create an LLM model from the given config."""
    if config.provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY", "placeholder")
        return OpenRouterModel(config.model, provider=OpenRouterProvider(api_key=api_key))
    raise ValueError(f"Unsupported LLM provider: {config.provider}")
