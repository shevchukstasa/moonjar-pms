"""
RAG embedding pipeline — index data into PostgreSQL.
Uses OpenAI embeddings stored as float[] + tsvector for full-text search.
No pgvector dependency required.
"""
import math
from uuid import UUID
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from api.config import get_settings
from api.models import RagEmbedding


EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using OpenAI API."""
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        return []

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={"input": text[:8000], "model": EMBEDDING_MODEL},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def index_entity(
    db: Session,
    entity_type: str,
    entity_id: UUID,
    text: str,
    metadata: Optional[dict] = None,
) -> RagEmbedding:
    """Index a text chunk into the embeddings table."""
    embedding = await generate_embedding(text)

    # Upsert: delete old entry for same source, insert new
    db.query(RagEmbedding).filter(
        RagEmbedding.source_table == entity_type,
        RagEmbedding.source_id == entity_id,
    ).delete()

    record = RagEmbedding(
        source_table=entity_type,
        source_id=entity_id,
        content_text=text,
        embedding=embedding if embedding else None,
        metadata_json=metadata or {},
    )
    db.add(record)
    db.flush()
    return record


async def index_order(db: Session, order_id: UUID):
    """Index order data for RAG search."""
    from api.models import ProductionOrder, OrderPosition

    order = db.query(ProductionOrder).filter(
        ProductionOrder.id == order_id
    ).first()
    if not order:
        return

    # Build text representation of the order
    positions = db.query(OrderPosition).filter(
        OrderPosition.order_id == order_id
    ).all()

    parts = [
        f"Order #{order.order_number}",
        f"Status: {order.status.value if hasattr(order.status, 'value') else order.status}",
        f"Source: {order.source.value if hasattr(order.source, 'value') else order.source}" if order.source else "",
        f"Customer: {order.customer_name}" if order.customer_name else "",
        f"Notes: {order.notes}" if order.notes else "",
    ]

    for p in positions:
        parts.append(
            f"Position: {p.product_type.value if hasattr(p.product_type, 'value') else p.product_type}"
            f" qty={p.quantity}"
            f" status={p.status.value if hasattr(p.status, 'value') else p.status}"
        )

    text = "\n".join(p for p in parts if p)

    await index_entity(
        db,
        entity_type="production_orders",
        entity_id=order_id,
        text=text,
        metadata={
            "order_number": order.order_number,
            "factory_id": str(order.factory_id) if order.factory_id else None,
        },
    )


async def index_recipe(db: Session, recipe_id: UUID):
    """Index recipe data for RAG search."""
    from api.models import GlazeRecipe

    recipe = db.query(GlazeRecipe).filter(
        GlazeRecipe.id == recipe_id
    ).first()
    if not recipe:
        return

    text = f"Glaze recipe: {recipe.name}"
    if hasattr(recipe, 'description') and recipe.description:
        text += f"\nDescription: {recipe.description}"
    if hasattr(recipe, 'notes') and recipe.notes:
        text += f"\nNotes: {recipe.notes}"

    await index_entity(
        db,
        entity_type="glaze_recipes",
        entity_id=recipe_id,
        text=text,
        metadata={"recipe_name": recipe.name},
    )
