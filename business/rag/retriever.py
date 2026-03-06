"""
RAG retriever — semantic search over pgvector embeddings.
"""
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session

from business.rag.embeddings import generate_embedding


async def search(db: Session, query: str, top_k: int = 5,
                 entity_type: Optional[str] = None,
                 factory_id: Optional[UUID] = None) -> list[dict]:
    """
    Semantic search: embed query → cosine similarity → top_k results.
    Optionally filter by entity_type and factory_id.
    """
    # TODO: implement
    # 1. Generate embedding for query
    # 2. SELECT * FROM embeddings ORDER BY embedding <=> query_vec LIMIT top_k
    # 3. Return [{text, metadata, score, entity_type, entity_id}]
    raise NotImplementedError


async def chat_with_context(db: Session, user_message: str,
                            session_id: UUID, factory_id: Optional[UUID] = None) -> str:
    """
    RAG chat: retrieve context → build prompt → call LLM → return answer.
    """
    # TODO: implement
    # 1. Retrieve relevant context
    # 2. Build system prompt with context
    # 3. Call OpenAI/Anthropic chat API
    # 4. Save to chat session
    # 5. Return answer
    raise NotImplementedError
