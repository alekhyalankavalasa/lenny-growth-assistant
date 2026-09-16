"""
Anthropic Claude provider.
Uses the official `anthropic` Python SDK.
"""
from typing import AsyncIterator

import structlog
import anthropic

from app.providers.base import LLMProvider, ProviderUnavailableError
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class AnthropicProvider:
    """Anthropic Claude via the official SDK."""

    def __init__(self):
        if not settings.anthropic_api_key:
            raise ProviderUnavailableError(
                "ANTHROPIC_API_KEY is not set. Cannot initialize Anthropic provider."
            )
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.cloud_model

    @property
    def name(self) -> str:
        return f"Anthropic {self._model}"

    async def chat_stream(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        kwargs = dict(
            model=self._model,
            max_tokens=max_tokens,
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.AuthenticationError as exc:
            raise ProviderUnavailableError(f"Anthropic auth failed: {exc}") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderUnavailableError(f"Anthropic unreachable: {exc}") from exc
        except Exception as exc:
            logger.error("anthropic.stream_error", error=str(exc))
            raise

    async def chat_complete(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> tuple[str, list[dict]]:
        kwargs = dict(
            model=self._model,
            max_tokens=max_tokens,
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        try:
            response = await self._client.messages.create(**kwargs)
            content = ""
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append({"name": block.name, "input": block.input, "id": block.id})
            return content, tool_calls
        except anthropic.AuthenticationError as exc:
            raise ProviderUnavailableError(f"Anthropic auth failed: {exc}") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderUnavailableError(f"Anthropic unreachable: {exc}") from exc
