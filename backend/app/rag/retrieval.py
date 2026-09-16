"""
RAG retrieval module.
Implements hybrid search: pgvector cosine similarity + tsvector full-text,
merged via Reciprocal Rank Fusion (RRF), with MMR deduplication.
Every result carries full source attribution (episode_title, source_file, chunk_index).
"""
import math
from typing import Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.rag.embedding import get_embedder

logger = structlog.get_logger(__name__)

# How many candidates to pull from each search arm before RRF merge
VECTOR_CANDIDATES = 20
TEXT_CANDIDATES = 20
RRF_K = 60  # standard RRF constant


async def retrieve(
    query: str,
    db: AsyncSession,
    top_k: int = 6,
    mmr_lambda: float = 0.7,
) -> list[dict]:
    """
    Retrieve top-K relevant chunks for a query using hybrid search.

    Returns:
        List of dicts with keys:
            - episode_title, source_file, source_type, chunk_index
            - content (full chunk text)
            - excerpt (first 250 chars)
            - score (RRF score)

    Returns empty list [] if no documents exist — caller must handle this.
    """
    # Step 1: Embed the query
    try:
        embedder = get_embedder()
        query_embeddings = await embedder.embed([query])
        query_vec = query_embeddings[0]
    except Exception as exc:
        logger.warning("retrieval.embed_failed", error=str(exc))
        # Fall back to text-only search
        query_vec = None

    chunks = []

    # Step 2: Vector search (if embedding succeeded)
    vector_results = {}
    if query_vec is not None:
        try:
            vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"
            result = await db.execute(
                text("""
                    SELECT
                        id::text,
                        episode_title,
                        source_file,
                        source_type,
                        chunk_index,
                        content,
                        1 - (embedding <=> CAST(:vec AS vector)) AS score
                    FROM documents
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:vec AS vector)
                    LIMIT :limit
                """),
                {"vec": vec_str, "limit": VECTOR_CANDIDATES},
            )
            rows = result.mappings().all()
            for rank, row in enumerate(rows):
                vector_results[row["id"]] = {
                    "rank": rank + 1,
                    "data": dict(row),
                }
        except Exception as exc:
            logger.warning("retrieval.vector_search_failed", error=str(exc))

    # Step 3: Full-text search
    text_results = {}
    try:
        result = await db.execute(
            text("""
                SELECT
                    id::text,
                    episode_title,
                    source_file,
                    source_type,
                    chunk_index,
                    content,
                    ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', :query)) AS score
                FROM documents
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', :query)
                ORDER BY score DESC
                LIMIT :limit
            """),
            {"query": query, "limit": TEXT_CANDIDATES},
        )
        rows = result.mappings().all()
        for rank, row in enumerate(rows):
            text_results[row["id"]] = {
                "rank": rank + 1,
                "data": dict(row),
            }
    except Exception as exc:
        logger.warning("retrieval.text_search_failed", error=str(exc))

    # Step 4: Reciprocal Rank Fusion
    all_ids = set(vector_results.keys()) | set(text_results.keys())
    if not all_ids:
        logger.info("retrieval.empty_results", query=query[:100])
        return []

    rrf_scores = {}
    for doc_id in all_ids:
        score = 0.0
        if doc_id in vector_results:
            score += 1.0 / (RRF_K + vector_results[doc_id]["rank"])
        if doc_id in text_results:
            score += 1.0 / (RRF_K + text_results[doc_id]["rank"])
        # Get data from whichever source has it
        data = (vector_results.get(doc_id) or text_results.get(doc_id))["data"]
        rrf_scores[doc_id] = {"score": score, "data": data}

    sorted_results = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)

    # Step 5: MMR deduplication (simple content-overlap based)
    selected = []
    candidates = [r["data"] for r in sorted_results]
    for _ in range(min(top_k, len(candidates))):
        if not candidates:
            break
        # Score = relevance - max_similarity_to_selected
        best_idx = 0
        best_score = -999
        for i, cand in enumerate(candidates):
            relevance = sorted_results[i]["score"] if i < len(sorted_results) else 0
            max_sim = max(
                (_overlap(cand["content"], sel["content"]) for sel in selected),
                default=0,
            )
            mmr_score = mmr_lambda * relevance - (1 - mmr_lambda) * max_sim
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i
        chosen = candidates.pop(best_idx)
        if best_idx < len(sorted_results):
            sorted_results.pop(best_idx)
        selected.append(chosen)

    # Step 6: Format output
    output = []
    for row in selected:
        output.append({
            "episode_title": row["episode_title"],
            "source_file": row["source_file"],
            "source_type": row["source_type"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "excerpt": row["content"][:250].strip() + "…" if len(row["content"]) > 250 else row["content"],
        })

    logger.info(
        "retrieval.complete",
        query=query[:80],
        results_found=len(output),
        top_source=output[0]["episode_title"] if output else "none",
    )
    return output


def _overlap(a: str, b: str) -> float:
    """Simple word-overlap similarity for MMR deduplication."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)
