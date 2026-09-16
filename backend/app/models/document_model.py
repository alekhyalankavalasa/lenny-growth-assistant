import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base

# Vector dimension constants
MINILM_EMBED_DIM = 384       # all-MiniLM-L6-v2


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_file: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # podcast | newsletter
    episode_title: Mapped[str] = mapped_column(String(512), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Dual-dimension embedding support
    # We store embedding_dim to detect model switches
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False, default=384)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384), nullable=True
    )

    # For full-text search (tsvector generated column via migration)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_documents_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
