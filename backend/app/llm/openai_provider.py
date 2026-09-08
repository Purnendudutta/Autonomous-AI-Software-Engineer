"""
OpenAI / OpenAI-compatible LLM and embedding provider.

Supports:
  - Official OpenAI API (default)
  - Any OpenAI-compatible endpoint (e.g. Azure OpenAI, Ollama, LM Studio, vLLM)
    by setting LLM_BASE_URL in environment.

API key is read from settings — never hard-coded.
"""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI, AuthenticationError, OpenAIError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.provider import EmbeddingProvider, LLMProvider, LLMResponse, Message

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """
    LLM provider backed by the OpenAI async SDK.

    Configuration is fully driven by Settings (env vars). No key is stored
    in this class beyond what is passed from Settings.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.llm_model
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens

        client_kwargs: dict[str, Any] = {
            "api_key": settings.openai_api_key or "not-set",
        }
        if settings.llm_base_url:
            client_kwargs["base_url"] = settings.llm_base_url

        self._client = AsyncOpenAI(**client_kwargs)
        logger.info(
            "llm_provider_initialized",
            provider="openai",
            model=self._model,
            has_base_url=bool(settings.llm_base_url),
        )

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Call the OpenAI chat completions endpoint."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature if temperature is not None else self._temperature,
            "max_tokens": max_tokens or self._max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = await self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                finish_reason=choice.finish_reason or "stop",
            )
        except AuthenticationError as exc:
            logger.error("llm_auth_error", error=str(exc))
            raise RuntimeError("LLM authentication failed. Check OPENAI_API_KEY.") from exc
        except OpenAIError as exc:
            logger.error("llm_api_error", error=str(exc))
            raise RuntimeError(f"LLM API error: {exc}") from exc

    async def health_check(self) -> bool:
        """Attempt a minimal API call to verify connectivity."""
        try:
            await self._client.models.retrieve(self._model)
            return True
        except Exception as exc:
            logger.warning("llm_health_check_failed", error=str(exc))
            return False


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenAI's embedding API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

        client_kwargs: dict[str, Any] = {
            "api_key": settings.openai_api_key or "not-set",
        }
        if settings.llm_base_url:
            client_kwargs["base_url"] = settings.llm_base_url

        self._client = AsyncOpenAI(**client_kwargs)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns a list of float vectors."""
        if not texts:
            return []
        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=texts,
                dimensions=self._dimensions,
            )
            # Sort by index to preserve order
            sorted_data = sorted(response.data, key=lambda d: d.index)
            return [item.embedding for item in sorted_data]
        except OpenAIError as exc:
            logger.error("embedding_api_error", error=str(exc))
            raise RuntimeError(f"Embedding API error: {exc}") from exc

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single text string."""
        vectors = await self.embed([text])
        return vectors[0]


def create_llm_provider() -> LLMProvider:
    """
    Factory function that returns the configured LLM provider.

    Add new providers here as elif branches.
    """
    settings = get_settings()
    if settings.llm_provider in ("openai", "openai_compatible"):
        return OpenAIProvider()
    raise ValueError(f"Unsupported LLM provider: '{settings.llm_provider}'")


def create_embedding_provider() -> EmbeddingProvider:
    """Factory function that returns the configured embedding provider."""
    settings = get_settings()
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider()
    raise ValueError(f"Unsupported embedding provider: '{settings.embedding_provider}'")
