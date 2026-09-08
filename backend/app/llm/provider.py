"""
LLM Provider abstraction layer.

All LLM calls in the agent must go through an LLMProvider instance.
This makes the model provider swappable via environment variables.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Message:
    """Simple message container (role + content)."""

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class LLMResponse:
    """Typed response from an LLM call."""

    def __init__(
        self,
        content: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        finish_reason: str = "stop",
    ) -> None:
        self.content = content
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.finish_reason = finish_reason


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Implement this interface to add a new model provider.
    The agent only interacts with this interface — never with the SDK directly.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of the provider (e.g. 'openai', 'anthropic')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier (e.g. 'gpt-4o', 'claude-3-5-sonnet')."""
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        Send a list of messages and return the LLM's response.

        Args:
            messages: Conversation history in role/content pairs.
            temperature: Override the provider's default temperature.
            max_tokens: Override the provider's default max_tokens.
            response_format: Optional JSON schema for structured output.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable and the API key is valid."""
        ...


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Return embeddings for a list of text strings.

        Args:
            texts: List of strings to embed.

        Returns:
            List of float vectors, one per input text.
        """
        ...

    @abstractmethod
    async def embed_single(self, text: str) -> list[float]:
        """Convenience method to embed a single string."""
        ...
