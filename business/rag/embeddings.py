"""
RAG embedding pipeline — index data into pgvector.
Uses OpenAI embeddings or local model.
"""
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session

from api.config import settings


EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using OpenAI API."""
    # TODO: implement — call OpenAI embeddings API
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     resp = await client.post(
    #         "https://api.openai.com/v1/embeddings",
    #         headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
    #         json={"input": text, "model": EMBEDDING_MODEL},
    #     )
    #     return resp.json()["data"][0]["embedding"]
    raise NotImplementedError


async def index_entity(db: Session, entity_type: str, entity_id: UUID,
                       text: str, metadata: Optional[dict] = None):
    """Index a text chunk into the embeddings table."""
    # TODO: implement
    raise NotImplementedError


async def index_order(db: Session, order_id: UUID):
    """Index order data for RAG search."""
    # TODO: implement
    raise NotImplementedError


async def index_recipe(db: Session, recipe_id: UUID):
    """Index recipe data for RAG search."""
    # TODO: implement
    raise NotImplementedError
