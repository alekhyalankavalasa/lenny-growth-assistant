"""Pydantic schemas for request/response validation."""
import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=255)
    user_id: Optional[str] = None


class SessionUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class SessionOut(BaseModel):
    id: uuid.UUID
    title: str
    user_id: Optional[str]
    provider_used: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Messages
# ─────────────────────────────────────────────────────────────────────────────

class Source(BaseModel):
    episode_title: str
    source_file: str
    source_type: str
    chunk_index: int
    excerpt: str  # first ~200 chars of the chunk


class MessageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    skill_used: Optional[str]
    sources: Optional[list[Source]]
    artifact_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Chat
# ─────────────────────────────────────────────────────────────────────────────

class SkillOverride(str):
    GROUNDED_QA = "grounded_qa"
    SHIP30_ESSAY = "ship30_essay"


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(..., min_length=1, max_length=8000)
    skill_override: Optional[str] = None  # "grounded_qa" | "ship30_essay"


class ChatChunk(BaseModel):
    """SSE chunk format."""
    type: str  # "delta" | "sources" | "artifact" | "done" | "error"
    delta: Optional[str] = None
    sources: Optional[list[Source]] = None
    artifact_id: Optional[str] = None
    skill_used: Optional[str] = None
    provider: Optional[str] = None
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Artifacts
# ─────────────────────────────────────────────────────────────────────────────

class ArtifactOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    type: str
    title: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    provider: str
    model: str


class ReadinessResponse(BaseModel):
    status: str  # "ok" | "degraded" | "error"
    db: dict[str, Any]
    provider: str
    model: str
    provider_reachable: bool


# ─────────────────────────────────────────────────────────────────────────────
# Error
# ─────────────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
