"""
OpenAI provider — uses the official openai Python SDK.
Also used for embeddings when LLM_PROVIDER=anthropic.
"""
from typing import AsyncIterator

import structlog
from openai import AsyncOpenAI, APIConnectionError, AuthenticationError

from app.providers.base import LLMProvider, ProviderUnavailableError
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class OpenAIProvider:
    """OpenAI GPT via the official SDK."""

    def __init__(self):
        if not settings.openai_api_key:
            raise ProviderUnavailableError(
                "OPENAI_API_KEY is not set. Cannot initialize OpenAI provider."
            )
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.cloud_model
        self._embedding_model = settings.embedding_model

    @property
    def name(self) -> str:
        return f"OpenAI {self._model}"

    async def chat_stream(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)

        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=msgs,
                stream=True,
                max_tokens=max_tokens,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except AuthenticationError as exc:
            raise ProviderUnavailableError(f"OpenAI auth failed: {exc}") from exc
        except APIConnectionError as exc:
            raise ProviderUnavailableError(f"OpenAI unreachable: {exc}") from exc

    async def chat_complete(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> tuple[str, list[dict]]:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=msgs,
                stream=False,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or "", []
        except AuthenticationError as exc:
            raise ProviderUnavailableError(f"OpenAI auth failed: {exc}") from exc
        except APIConnectionError as exc:
            raise ProviderUnavailableError(f"OpenAI unreachable: {exc}") from exc
