"""
Ollama provider — uses Ollama's OpenAI-compatible /v1 API.
This means we use the `openai` Python SDK pointed at localhost:11434.
No code changes needed when switching between Ollama and OpenAI.
"""
from typing import AsyncIterator

import httpx
import structlog
from openai import AsyncOpenAI, APIConnectionError, AuthenticationError

from app.providers.base import LLMProvider, ProviderUnavailableError
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class OllamaProvider:
    """Local Ollama via its OpenAI-compatible API."""

    def __init__(self):
        self._base_url = settings.ollama_base_url
        self._model = settings.ollama_model
        self._embedding_model = settings.ollama_embedding_model
        self._client = AsyncOpenAI(
            base_url=f"{self._base_url}/v1",
            api_key="ollama",  # required field but ignored by Ollama
        )

    @property
    def name(self) -> str:
        return f"Ollama {self._model}"

    async def _check_health(self) -> None:
        """Pre-flight: verify Ollama is running."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                if resp.status_code != 200:
                    raise ProviderUnavailableError(
                        f"Ollama returned HTTP {resp.status_code}. Is it running?"
                    )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(
                f"Ollama is not reachable at {self._base_url}. "
                "Start Ollama with `ollama serve` or check OLLAMA_BASE_URL in .env."
            ) from exc

    async def chat_stream(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        await self._check_health()

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
        except APIConnectionError as exc:
            raise ProviderUnavailableError(f"Ollama connection failed: {exc}") from exc

    async def chat_complete(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> tuple[str, list[dict]]:
        await self._check_health()

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
            content = response.choices[0].message.content or ""
            return content, []
        except APIConnectionError as exc:
            raise ProviderUnavailableError(f"Ollama connection failed: {exc}") from exc

