"""Embedding provider factory."""

from pydantic_ai import Embedder
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.providers.openai import OpenAIProvider

from loom.settings import EmbeddingConfig


def create_embedder(config: EmbeddingConfig) -> Embedder:
    """Create an Embedder from config. All provider details come from settings."""
    provider = OpenAIProvider(
        api_key=config.api_key,
        base_url=config.base_url,
    )
    model = OpenAIEmbeddingModel(config.model, provider=provider)
    return Embedder(model)
