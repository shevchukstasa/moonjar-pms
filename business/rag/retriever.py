"""
RAG retriever — hybrid search: PostgreSQL full-text + cosine similarity.
No pgvector dependency — works on any PostgreSQL instance.
"""
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text

from api.models import RagEmbedding
from business.rag.embeddings import generate_embedding, cosine_similarity


async def search(
    db: Session,
    query: str,
    top_k: int = 5,
    entity_type: Optional[str] = None,
    factory_id: Optional[UUID] = None,
) -> list[dict]:
    """
    Hybrid search: full-text (tsvector) + semantic (cosine similarity).
    Returns top_k results sorted by combined relevance score.
    """
    results = []

    # --- Strategy 1: Full-text search (fast, keyword-based) ---
    fts_results = _fulltext_search(
        db, query, top_k=top_k * 2,
        entity_type=entity_type, factory_id=factory_id,
    )
    for r in fts_results:
        results.append({
            "id": str(r.id),
            "source_table": r.source_table,
            "source_id": str(r.source_id),
            "content_text": r.content_text,
            "metadata": r.metadata_json or {},
            "score": r.fts_rank if hasattr(r, "fts_rank") else 0.5,
            "method": "fulltext",
        })

    # --- Strategy 2: Semantic search (slower, meaning-based) ---
    try:
        query_embedding = await generate_embedding(query)
        if query_embedding:
            semantic_results = _semantic_search(
                db, query_embedding, top_k=top_k * 2,
                entity_type=entity_type, factory_id=factory_id,
            )
            for item in semantic_results:
                results.append({
                    "id": str(item["id"]),
                    "source_table": item["source_table"],
                    "source_id": str(item["source_id"]),
                    "content_text": item["content_text"],
                    "metadata": item["metadata"],
                    "score": item["score"],
                    "method": "semantic",
                })
    except Exception:
        pass  # Semantic search is optional; full-text still works

    # --- Merge & deduplicate by source_id, keep highest score ---
    seen = {}
    for r in results:
        key = r["source_id"]
        if key not in seen or r["score"] > seen[key]["score"]:
            seen[key] = r
    merged = sorted(seen.values(), key=lambda x: x["score"], reverse=True)

    return merged[:top_k]


def _fulltext_search(
    db: Session,
    query: str,
    top_k: int = 10,
    entity_type: Optional[str] = None,
    factory_id: Optional[UUID] = None,
) -> list:
    """PostgreSQL full-text search using to_tsvector/to_tsquery."""
    # Build plainto_tsquery for safe query parsing
    sql = """
        SELECT id, source_table, source_id, content_text, metadata_json,
               ts_rank(
                   to_tsvector('simple', content_text),
                   plainto_tsquery('simple', :query)
               ) AS fts_rank
        FROM rag_embeddings
        WHERE to_tsvector('simple', content_text) @@ plainto_tsquery('simple', :query)
    """
    params = {"query": query}

    if entity_type:
        sql += " AND source_table = :entity_type"
        params["entity_type"] = entity_type

    if factory_id:
        sql += " AND metadata_json->>'factory_id' = :factory_id"
        params["factory_id"] = str(factory_id)

    sql += " ORDER BY fts_rank DESC LIMIT :limit"
    params["limit"] = top_k

    rows = db.execute(sa_text(sql), params).fetchall()
    return rows


def _semantic_search(
    db: Session,
    query_embedding: list[float],
    top_k: int = 10,
    entity_type: Optional[str] = None,
    factory_id: Optional[UUID] = None,
) -> list[dict]:
    """App-level cosine similarity search over stored float[] embeddings."""
    # Fetch candidates (with embeddings)
    q = db.query(RagEmbedding).filter(RagEmbedding.embedding.isnot(None))

    if entity_type:
        q = q.filter(RagEmbedding.source_table == entity_type)

    if factory_id:
        q = q.filter(
            RagEmbedding.metadata_json["factory_id"].astext == str(factory_id)
        )

    # For large datasets (>50K), paginate or use pre-filtering
    candidates = q.limit(5000).all()

    scored = []
    for c in candidates:
        sim = cosine_similarity(query_embedding, c.embedding)
        scored.append({
            "id": c.id,
            "source_table": c.source_table,
            "source_id": c.source_id,
            "content_text": c.content_text,
            "metadata": c.metadata_json or {},
            "score": sim,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# chat_with_context — removed (replaced by ai_chat_service.py which supports
# Anthropic→OpenAI fallback, session history, RAG sources, auto-naming)
