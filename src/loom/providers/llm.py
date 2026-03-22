"""LLM provider factory."""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from loom.settings import LLMConfig


def create_llm_model(config: LLMConfig) -> OpenAIChatModel:
    """Create an LLM model from config. All provider details come from settings."""
    provider = OpenAIProvider(
        api_key=config.api_key,
        base_url=config.base_url,
    )
    return OpenAIChatModel(config.model, provider=provider)
