"""
Chat router — the core SSE streaming endpoint.
Orchestrates: skill routing → retrieval → LLM streaming → artifact creation → DB persistence.
"""
import asyncio
import json
import uuid
from typing import AsyncIterator

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db_session, AsyncSessionLocal
from app.models.session_model import Session
from app.models.message_model import Message
from app.models.artifact_model import Artifact
from app.agent.router import route_message
from app.agent.skills import (
    build_grounded_qa_messages,
    build_ship30_messages,
    SkillResult,
)
from app.agent.sanitize import sanitize_markdown_to_text
from app.rag.retrieval import retrieve
from app.providers.factory import get_provider
from app.providers.base import ProviderUnavailableError
from app.schemas import ChatRequest, Source

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])
settings = get_settings()


def _sse_event(data: dict) -> str:
    """Format a dict as an SSE data event."""
    return f"data: {json.dumps(data)}\n\n"


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Main chat endpoint. Streams response via Server-Sent Events (SSE).

    SSE event types:
      {"type": "delta", "delta": "..."}         — streaming token
      {"type": "sources", "sources": [...]}      — retrieved sources (sent once)
      {"type": "artifact", "artifact_id": "...","skill_used":"..."} — artifact created
      {"type": "done", "provider": "..."}        — stream complete
      {"type": "error", "error": "..."}          — error occurred
    """
    # Verify session exists
    result = await db.execute(select(Session).where(Session.id == payload.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get message history for context
    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == payload.session_id)
        .order_by(Message.created_at.asc())
        .limit(20)  # last 20 messages for context window
    )
    history_messages = [
        {"role": m.role, "content": m.content}
        for m in history_result.scalars().all()
    ]

    return StreamingResponse(
        _stream_response(payload, session, history_messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_response(
    payload: ChatRequest,
    session: Session,
    history: list[dict],
) -> AsyncIterator[str]:
    """Core streaming generator."""
    provider = get_provider()
    full_content = ""
    sources = []
    artifact_id = None
    skill_name = route_message(payload.message, payload.skill_override)

    try:
        # ── Retrieval ──────────────────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            try:
                sources = await retrieve(
                    query=payload.message,
                    db=db,
                    top_k=settings.rag_top_k,
                )
            except Exception as exc:
                logger.warning("chat.retrieval_failed", error=str(exc))
                sources = []

        # Send sources event immediately (before generation starts)
        source_objs = [
            Source(
                episode_title=s["episode_title"],
                source_file=s["source_file"],
                source_type=s["source_type"],
                chunk_index=s["chunk_index"],
                excerpt=s["excerpt"],
            ).model_dump()
            for s in sources
        ]
        if source_objs:
            yield _sse_event({"type": "sources", "sources": source_objs})

        # ── Build messages for selected skill ──────────────────────────────
        if skill_name == "ship30_essay":
            system, messages = build_ship30_messages(
                payload.message, history, sources
            )
        else:
            system, messages = build_grounded_qa_messages(
                payload.message, history, sources
            )

        # ── Stream LLM response ────────────────────────────────────────────
        try:
            async for delta in provider.chat_stream(
                messages=messages,
                system=system,
                max_tokens=settings.max_tokens,
            ):
                full_content += delta
                yield _sse_event({"type": "delta", "delta": delta})

        except ProviderUnavailableError as exc:
            error_msg = str(exc)
            logger.error("chat.provider_unavailable", error=error_msg, skill=skill_name)
            yield _sse_event({"type": "error", "error": error_msg})
            return

        except asyncio.TimeoutError:
            yield _sse_event({
                "type": "error",
                "error": "The model took too long to respond. Please try again.",
            })
            return

        # ── Create artifact for Ship 30 essays ────────────────────────────
        if skill_name == "ship30_essay" and full_content:
            clean_content = sanitize_markdown_to_text(full_content)
            # Extract title from first H1 or H2
            title = _extract_title(clean_content) or "Ship 30 Essay"

            async with AsyncSessionLocal() as db:
                artifact = Artifact(
                    session_id=payload.session_id,
                    type="markdown",
                    title=title,
                    content=clean_content,
                )
                db.add(artifact)
                await db.flush()
                await db.refresh(artifact)
                artifact_id = str(artifact.id)
                await db.commit()

            yield _sse_event({
                "type": "artifact",
                "artifact_id": artifact_id,
                "artifact_title": title,
                "skill_used": skill_name,
            })

        # ── Persist user + assistant messages ─────────────────────────────
        async with AsyncSessionLocal() as db:
            # Save user message
            user_msg = Message(
                session_id=payload.session_id,
                role="user",
                content=payload.message,
            )
            db.add(user_msg)

            # Save assistant message
            assistant_msg = Message(
                session_id=payload.session_id,
                role="assistant",
                content=full_content,
                skill_used=skill_name,
                sources=source_objs if source_objs else None,
                artifact_id=uuid.UUID(artifact_id) if artifact_id else None,
            )
            db.add(assistant_msg)

            # Update session with provider info
            result = await db.execute(
                select(Session).where(Session.id == payload.session_id)
            )
            sess = result.scalar_one_or_none()
            if sess:
                sess.provider_used = provider.name
            await db.commit()

        # ── Done ──────────────────────────────────────────────────────────
        yield _sse_event({"type": "done", "provider": provider.name, "skill_used": skill_name})

    except Exception as exc:
        logger.error("chat.unexpected_error", error=str(exc), exc_info=True)
        yield _sse_event({
            "type": "error",
            "error": "An unexpected error occurred. Please try again.",
        })


def _extract_title(markdown: str) -> str | None:
    """Extract first heading from markdown as the artifact title."""
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped.startswith("## "):
            return stripped[3:].strip()
    return None
