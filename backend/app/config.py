"""
Application configuration — driven by environment variables.
All settings are read from .env via pydantic-settings.
Switch LLM providers by changing LLM_PROVIDER in .env — no code changes needed.
"""
from enum import Enum
from typing import Optional
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "changeme"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # ── LLM Provider ─────────────────────────────────────────────────────────
    llm_provider: LLMProvider = LLMProvider.OLLAMA
    llm_fallback_to_ollama: bool = True
    cloud_model: str = "claude-sonnet-4-5"
    max_tokens: int = 4096
    llm_timeout_seconds: int = 60

    # ── Anthropic ─────────────────────────────────────────────────────────────
    anthropic_api_key: Optional[str] = None

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"

    # ── Ollama ───────────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://lenny:lenny_secret@localhost:5432/lenny_db"

    # ── RAG ───────────────────────────────────────────────────────────────────
    rag_top_k: int = 6
    backend_port: int = 8000

    # ── Derived: active embedding model ──────────────────────────────────────
    @property
    def active_embedding_model(self) -> str:
        if self.llm_provider == LLMProvider.OLLAMA:
            return self.ollama_embedding_model
        return self.embedding_model

    @property
    def active_chat_model(self) -> str:
        if self.llm_provider == LLMProvider.OLLAMA:
            return self.ollama_model
        return self.cloud_model

    @model_validator(mode="after")
    def validate_provider_keys(self) -> "Settings":
        """Warn (not error) if cloud provider is selected but key is missing."""
        if self.llm_provider == LLMProvider.ANTHROPIC and not self.anthropic_api_key:
            import warnings
            warnings.warn(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
                "Will attempt Ollama fallback if LLM_FALLBACK_TO_OLLAMA=true.",
                stacklevel=2,
            )
        if self.llm_provider == LLMProvider.OPENAI and not self.openai_api_key:
            import warnings
            warnings.warn(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. "
                "Will attempt Ollama fallback if LLM_FALLBACK_TO_OLLAMA=true.",
                stacklevel=2,
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
