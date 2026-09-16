"""Session management endpoints."""
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.session_model import Session
from app.models.message_model import Message
from app.schemas import SessionCreate, SessionUpdate, SessionOut, MessageOut

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new isolated chat session."""
    session = Session(title=payload.title, user_id=payload.user_id)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    logger.info("session.created", session_id=str(session.id))
    return session


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
):
    """List recent sessions."""
    result = await db.execute(
        select(Session).order_by(Session.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def get_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get all messages for a session (ordered by time)."""
    # Verify session exists
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a session and all its messages/artifacts (cascade)."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    logger.info("session.deleted", session_id=str(session_id))


@router.patch("/{session_id}", response_model=SessionOut)
async def update_session(
    session_id: uuid.UUID,
    payload: SessionUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update a session's title."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.title = payload.title
    await db.commit()
    await db.refresh(session)
    logger.info("session.updated", session_id=str(session_id), new_title=session.title)
    return session
