#!/usr/bin/env python3
"""
Transcript ingestion script.
Downloads Lenny's public starter pack from GitHub, parses markdown transcripts,
chunks them, embeds each chunk, and upserts into the documents table.

Usage:
    python scripts/ingest_transcripts.py [--corpus-dir PATH] [--skip-download]

The starter pack (~50 podcast + 10 newsletter transcripts) is cloned from:
    https://github.com/lennyspodcast/transcripts  (public, free)

Assumption A1: We use this free starter pack. Full corpus requires a paid
lennysdata.com subscription. See PRD.md for details.
"""
import asyncio
import hashlib
import os
import re
import sys
import json
import argparse
from pathlib import Path

import httpx
import structlog
from tqdm import tqdm
from sqlalchemy import text

# Ensure the backend app is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.database import engine, AsyncSessionLocal, init_db
from app.models.document_model import Document
from app.providers.factory import get_provider
from app.rag.embedding import get_embedder

logger = structlog.get_logger(__name__)
settings = get_settings()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

CORPUS_REPO = "https://api.github.com/repos/lennyspodcast/transcripts/git/trees/main?recursive=1"
RAW_BASE = "https://raw.githubusercontent.com/lennyspodcast/transcripts/main"
CHUNK_SIZE_TOKENS = 400   # target tokens per chunk
CHUNK_OVERLAP_TOKENS = 80 # overlap to preserve context at boundaries
APPROX_CHARS_PER_TOKEN = 4  # rough approximation (avoids tiktoken dependency in Docker)

DATA_DIR = Path(__file__).parent.parent / "data" / "transcripts"
EMBED_DIM = 384  # all-MiniLM-L6-v2 output dimension


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Download corpus
# ─────────────────────────────────────────────────────────────────────────────

async def download_corpus(data_dir: Path) -> list[Path]:
    """Clone or update the public transcript repo."""
    data_dir.mkdir(parents=True, exist_ok=True)

    logger.info("ingestion.fetching_file_list", repo=CORPUS_REPO)
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(CORPUS_REPO)
            resp.raise_for_status()
        except Exception as exc:
            logger.error(
                "ingestion.fetch_failed",
                error=str(exc),
                hint="Check network access or provide --corpus-dir with local transcripts",
            )
            raise

    tree = resp.json().get("tree", [])
    md_files = [f for f in tree if f["path"].endswith(".md")]
    logger.info("ingestion.files_found", count=len(md_files))

    downloaded = []
    async with httpx.AsyncClient(timeout=60) as client:
        for file_info in tqdm(md_files, desc="Downloading transcripts"):
            local_path = data_dir / file_info["path"]
            local_path.parent.mkdir(parents=True, exist_ok=True)

            if local_path.exists():
                downloaded.append(local_path)
                continue

            raw_url = f"{RAW_BASE}/{file_info['path']}"
            try:
                resp = await client.get(raw_url)
                resp.raise_for_status()
                local_path.write_text(resp.text, encoding="utf-8")
                downloaded.append(local_path)
            except Exception as exc:
                logger.warning("ingestion.file_download_failed", path=file_info["path"], error=str(exc))

    logger.info("ingestion.download_complete", files=len(downloaded))
    return downloaded


def load_local_corpus(data_dir: Path) -> list[Path]:
    """Load markdown files from a local directory."""
    files = list(data_dir.rglob("*.md"))
    logger.info("ingestion.local_files_found", count=len(files), dir=str(data_dir))
    return files


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Parse transcripts
# ─────────────────────────────────────────────────────────────────────────────

def parse_transcript(filepath: Path) -> dict:
    """
    Parse a markdown transcript file into structured metadata + content.
    Expected frontmatter format:
        ---
        title: "Episode Title"
        date: "2024-01-15"
        type: podcast  # or newsletter
        url: https://...
        ---
        [body content]
    """
    text = filepath.read_text(encoding="utf-8", errors="replace")

    # Extract YAML-like frontmatter
    metadata = {
        "episode_title": filepath.stem,
        "source_file": filepath.name,
        "source_type": _infer_type(filepath),
        "url": "",
    }

    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if frontmatter_match:
        fm_text = frontmatter_match.group(1)
        for line in fm_text.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip().strip('"').strip("'")
                if key == "title":
                    metadata["episode_title"] = value
                elif key == "type":
                    metadata["source_type"] = value
                elif key == "url":
                    metadata["url"] = value
        body = text[frontmatter_match.end():]
    else:
        # Try to extract title from first H1
        h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if h1_match:
            metadata["episode_title"] = h1_match.group(1).strip()
        body = text

    return {"metadata": metadata, "body": body}


def _infer_type(filepath: Path) -> str:
    """Guess podcast vs newsletter from path/filename."""
    path_str = str(filepath).lower()
    if "newsletter" in path_str:
        return "newsletter"
    if "podcast" in path_str or "episode" in path_str:
        return "podcast"
    return "podcast"  # default


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Chunk
# ─────────────────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size_chars: int = None, overlap_chars: int = None) -> list[str]:
    """
    Split text into overlapping chunks, preferring paragraph boundaries.
    """
    if chunk_size_chars is None:
        chunk_size_chars = CHUNK_SIZE_TOKENS * APPROX_CHARS_PER_TOKEN
    if overlap_chars is None:
        overlap_chars = CHUNK_OVERLAP_TOKENS * APPROX_CHARS_PER_TOKEN

    # Split on paragraph breaks first
    paragraphs = re.split(r"\n{2,}", text.strip())
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= chunk_size_chars:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
                # Keep overlap from end of current chunk
                current = current[-overlap_chars:] + "\n\n" + para if overlap_chars > 0 else para
            else:
                # Single paragraph exceeds chunk size — split by sentence
                sentences = re.split(r"(?<=[.!?])\s+", para)
                sub = ""
                for sent in sentences:
                    if len(sub) + len(sent) <= chunk_size_chars:
                        sub = (sub + " " + sent).strip()
                    else:
                        if sub:
                            chunks.append(sub)
                        sub = sent
                if sub:
                    current = sub

    if current:
        chunks.append(current)

    # Filter empty/tiny chunks
    return [c for c in chunks if len(c.strip()) > 50]


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Embed + upsert
# ─────────────────────────────────────────────────────────────────────────────

def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:64]


def pad_or_truncate_embedding(embedding: list[float], target_dim: int = 1536) -> list[float]:
    """Ensure embedding is exactly target_dim (for nomic-embed-text at 768 dims)."""
    if len(embedding) == target_dim:
        return embedding
    if len(embedding) < target_dim:
        return embedding + [0.0] * (target_dim - len(embedding))
    return embedding[:target_dim]


async def ingest_file(filepath: Path, embedder, session) -> int:
    """Ingest a single transcript file. Returns number of chunks inserted."""
    parsed = parse_transcript(filepath)
    meta = parsed["metadata"]
    chunks = chunk_text(parsed["body"])

    if not chunks:
        logger.warning("ingestion.no_chunks", file=filepath.name)
        return 0

    # Batch embed all chunks
    try:
        embeddings = await embedder.embed(chunks)
    except Exception as exc:
        logger.error("ingestion.embed_failed", file=filepath.name, error=str(exc))
        embeddings = [None] * len(chunks)

    inserted = 0
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_hash = content_hash(chunk)

        # Idempotent: skip if already exists
        existing = await session.execute(
            text("SELECT id FROM documents WHERE content_hash = :hash"),
            {"hash": chunk_hash},
        )
        if existing.scalar_one_or_none():
            continue

        if embedding:
            embedding = pad_or_truncate_embedding(embedding, EMBED_DIM)

        doc = Document(
            source_file=meta["source_file"],
            source_type=meta["source_type"],
            episode_title=meta["episode_title"],
            chunk_index=idx,
            content=chunk,
            content_hash=chunk_hash,
            embedding_dim=len(embedding) if embedding else EMBED_DIM,
            embedding=embedding,
        )
        session.add(doc)
        inserted += 1

    if inserted > 0:
        await session.commit()

    return inserted


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

async def main(corpus_dir: Path, skip_download: bool):
    logger.info("ingestion.start", corpus_dir=str(corpus_dir), skip_download=skip_download)

    # Init DB
    await init_db()

    # Get embedder
    embedder = get_embedder()
    logger.info("ingestion.embedder", model=embedder.model_name)

    # Get files
    if skip_download:
        files = load_local_corpus(corpus_dir)
    else:
        files = await download_corpus(corpus_dir)

    if not files:
        logger.error("ingestion.no_files_found", corpus_dir=str(corpus_dir))
        sys.exit(1)

    # Ingest
    total_chunks = 0
    async with AsyncSessionLocal() as session:
        for filepath in tqdm(files, desc="Ingesting transcripts"):
            try:
                n = await ingest_file(filepath, embedder, session)
                total_chunks += n
                if n > 0:
                    logger.info("ingestion.file_done", file=filepath.name, chunks=n)
            except Exception as exc:
                logger.error("ingestion.file_failed", file=filepath.name, error=str(exc))

    logger.info("ingestion.complete", total_chunks=total_chunks, files_processed=len(files))
    print(f"\n✅ Ingestion complete: {total_chunks} chunks from {len(files)} files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Lenny transcripts into the knowledge base")
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=DATA_DIR,
        help="Local directory for transcript files",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip GitHub download and use local files only",
    )
    args = parser.parse_args()
    asyncio.run(main(args.corpus_dir, args.skip_download))
