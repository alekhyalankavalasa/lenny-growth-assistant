"""Health check endpoints."""
import httpx
from fastapi import APIRouter

from app.config import get_settings
from app.database import check_db_health
from app.schemas import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def liveness():
    """Liveness probe — always returns 200 if the process is running."""
    return HealthResponse(
        status="ok",
        provider=settings.llm_provider.value,
        model=settings.active_chat_model,
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness():
    """
    Readiness probe — checks DB connectivity and provider reachability.
    Returns 503 if critical dependencies are unavailable.
    """
    from fastapi import Response
    db_status = await check_db_health()
    provider_reachable = await _check_provider()

    overall = "ok" if db_status["status"] == "connected" and provider_reachable else "degraded"

    return ReadinessResponse(
        status=overall,
        db=db_status,
        provider=settings.llm_provider.value,
        model=settings.active_chat_model,
        provider_reachable=provider_reachable,
    )


async def _check_provider() -> bool:
    """Check if the active LLM provider is reachable."""
    provider = settings.llm_provider.value
    try:
        if provider == "ollama":
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                return resp.status_code == 200
        elif provider == "anthropic":
            return bool(settings.anthropic_api_key)
        elif provider == "openai":
            return bool(settings.openai_api_key)
    except Exception:
        return False
    return False
