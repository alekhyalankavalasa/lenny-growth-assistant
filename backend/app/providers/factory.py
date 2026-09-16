"""
Provider factory — returns the correct provider based on LLM_PROVIDER env var.
Implements fallback to Ollama if cloud provider is unavailable.
"""
import structlog

from app.config import get_settings, LLMProvider
from app.providers.base import ProviderUnavailableError

logger = structlog.get_logger(__name__)
settings = get_settings()

# Module-level singleton cache
_provider_instance = None


def get_provider():
    """
    Returns the active LLM provider singleton.
    On failure, falls back to Ollama if LLM_FALLBACK_TO_OLLAMA=true.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    _provider_instance = _create_provider(settings.llm_provider)
    return _provider_instance


def _create_provider(provider_type: LLMProvider):
    """Instantiate provider; fall back to Ollama on failure if configured."""
    try:
        if provider_type == LLMProvider.ANTHROPIC:
            from app.providers.anthropic_provider import AnthropicProvider
            instance = AnthropicProvider()
            logger.info("provider.initialized", provider="anthropic", model=settings.cloud_model)
            return instance

        elif provider_type == LLMProvider.OPENAI:
            from app.providers.openai_provider import OpenAIProvider
            instance = OpenAIProvider()
            logger.info("provider.initialized", provider="openai", model=settings.cloud_model)
            return instance

        elif provider_type == LLMProvider.OLLAMA:
            from app.providers.ollama_provider import OllamaProvider
            instance = OllamaProvider()
            logger.info("provider.initialized", provider="ollama", model=settings.ollama_model)
            return instance

    except ProviderUnavailableError as exc:
        if settings.llm_fallback_to_ollama and provider_type != LLMProvider.OLLAMA:
            logger.warning(
                "provider.fallback",
                original_provider=provider_type.value,
                reason=str(exc),
                fallback="ollama",
            )
            return _create_provider(LLMProvider.OLLAMA)
        raise


def reset_provider():
    """Reset singleton — useful for testing or dynamic provider switches."""
    global _provider_instance
    _provider_instance = None
