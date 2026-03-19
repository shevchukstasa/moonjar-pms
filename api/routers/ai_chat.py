"""AI Chat router — RAG-based assistant.
See API_CONTRACTS.md for full specification.
"""

import logging
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.database import get_db
from api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas (kept local — small, endpoint-specific)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None  # None = create new session


class ChatResponse(BaseModel):
    session_id: str
    message: str
    sources: list[dict] = []


class SessionItem(BaseModel):
    id: str
    session_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class MessageItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: Optional[str] = None
    sources: list[dict] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_factory_ids(db: Session, user_id: UUID) -> list[UUID]:
    """Get factory IDs assigned to user."""
    from api.models import UserFactory
    rows = (
        db.query(UserFactory.factory_id)
        .filter(UserFactory.user_id == user_id)
        .all()
    )
    return [r[0] for r in rows]


def _get_factory_names(db: Session, factory_ids: list[UUID]) -> list[str]:
    """Resolve factory IDs to names."""
    if not factory_ids:
        return []
    from api.models import Factory
    rows = (
        db.query(Factory.name)
        .filter(Factory.id.in_(factory_ids))
        .all()
    )
    return [r[0] for r in rows]


def _get_or_create_session(
    db: Session,
    user_id: UUID,
    session_id: Optional[str],
) -> "AiChatHistory":
    """Get existing session or create a new one."""
    from api.models import AiChatHistory

    if session_id:
        session = db.query(AiChatHistory).filter(
            AiChatHistory.id == session_id,
            AiChatHistory.user_id == user_id,
        ).first()
        if not session:
            raise HTTPException(404, "Chat session not found")
        return session

    # Create new session
    session = AiChatHistory(
        id=uuid4(),
        user_id=user_id,
        messages_json=[],
        session_name=None,
    )
    db.add(session)
    db.flush()
    return session


def _auto_name_session(user_message: str) -> str:
    """Generate a short session name from the first user message."""
    name = user_message.strip()[:80]
    if len(user_message) > 80:
        name += "..."
    return name


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Send a message to the AI assistant.

    Flow:
    1. Get or create chat session
    2. Save user message to session history
    3. Search RAG for relevant context
    4. Build prompt with context + conversation history
    5. Call LLM (Anthropic → OpenAI → fallback)
    6. Save assistant message
    7. Return response with sources
    """
    from business.rag.retriever import search as rag_search
    from business.services.ai_chat_service import generate_response

    user_id = current_user.id

    # 1. Session
    session = _get_or_create_session(db, user_id, request.session_id)

    # Auto-name new sessions from first message
    if not session.session_name:
        session.session_name = _auto_name_session(request.message)

    # 2. Save user message
    messages = session.messages_json if session.messages_json else []
    now_iso = datetime.now(timezone.utc).isoformat()
    messages.append({
        "role": "user",
        "content": request.message,
        "timestamp": now_iso,
    })

    # 3. RAG search — scope to user's first factory if available
    factory_ids = _get_user_factory_ids(db, user_id)
    first_factory = factory_ids[0] if factory_ids else None

    try:
        rag_results = await rag_search(
            db,
            query=request.message,
            top_k=5,
            factory_id=first_factory,
        )
    except Exception as e:
        logger.warning("RAG search failed: %s", e)
        rag_results = []

    # 4-5. Generate LLM response
    factory_names = _get_factory_names(db, factory_ids)
    conversation_history = [
        {"role": m["role"], "content": m["content"]}
        for m in messages[:-1]  # exclude current message (passed separately)
    ]

    try:
        response_text, provider = await generate_response(
            user_message=request.message,
            context=rag_results,
            conversation_history=conversation_history,
            factory_names=factory_names,
        )
    except Exception as e:
        logger.error("LLM generation failed: %s", e)
        response_text = "Sorry, an error occurred while generating a response. Please try again."
        provider = "error"

    # 6. Save assistant message
    sources = [
        {
            "source_table": r.get("source_table", ""),
            "source_id": r.get("source_id", ""),
            "score": round(r.get("score", 0), 3),
            "preview": (r.get("content_text", "")[:200] + "...")
            if len(r.get("content_text", "")) > 200
            else r.get("content_text", ""),
        }
        for r in rag_results
    ]

    messages.append({
        "role": "assistant",
        "content": response_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "provider": provider,
    })

    session.messages_json = messages
    session.updated_at = datetime.now(timezone.utc)
    db.commit()

    return ChatResponse(
        session_id=str(session.id),
        message=response_text,
        sources=sources,
    )


@router.get("/sessions", response_model=list[SessionItem])
async def list_chat_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List user's chat sessions, most recent first."""
    from api.models import AiChatHistory

    sessions = (
        db.query(AiChatHistory)
        .filter(AiChatHistory.user_id == current_user.id)
        .order_by(AiChatHistory.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        SessionItem(
            id=str(s.id),
            session_name=s.session_name,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=len(s.messages_json) if s.messages_json else 0,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[MessageItem])
async def get_chat_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all messages in a chat session."""
    from api.models import AiChatHistory

    session = db.query(AiChatHistory).filter(
        AiChatHistory.id == session_id,
        AiChatHistory.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(404, "Chat session not found")

    messages = session.messages_json if session.messages_json else []

    return [
        MessageItem(
            role=m.get("role", "user"),
            content=m.get("content", ""),
            timestamp=m.get("timestamp"),
            sources=m.get("sources", []),
        )
        for m in messages
    ]
