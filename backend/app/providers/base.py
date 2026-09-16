"""
LLM Provider base interface.
All providers must implement this protocol so they are swappable
by changing LLM_PROVIDER in .env — no application code changes needed.
"""
from typing import AsyncIterator, Protocol, runtime_checkable


class ProviderUnavailableError(Exception):
    """Raised when the configured LLM provider is unreachable or misconfigured."""
    pass


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal interface every provider must satisfy."""

    @property
    def name(self) -> str:
        """Human-readable provider name (e.g. 'Anthropic claude-sonnet-4-5')."""
        ...

    async def chat_stream(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """
        Stream chat completions token by token.
        Yields string deltas (partial tokens).
        Raises ProviderUnavailableError if provider is unreachable.
        """
        ...

    async def chat_complete(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> tuple[str, list[dict]]:
        """
        Non-streaming completion.
        Returns (content, tool_calls_list).
        """
        ...

