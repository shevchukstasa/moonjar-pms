"""
AI Chat service — LLM integration for RAG-based assistant.
Uses httpx directly (no SDK dependencies).

Priority: Anthropic Claude → OpenAI → fallback (context-only response).
"""

import os
import logging
from typing import Optional

import httpx

from api.config import get_settings

logger = logging.getLogger(__name__)

# Maximum conversation history messages to include in LLM context
MAX_HISTORY_MESSAGES = 20

SYSTEM_PROMPT_TEMPLATE = (
    "You are an AI assistant for Moonjar PMS, a stone product manufacturing "
    "management system. You help production managers, owners, and staff with "
    "questions about orders, materials, kiln schedules, quality, and production "
    "workflows.\n\n"
    "Guidelines:\n"
    "- Answer based on the provided context from the production database.\n"
    "- If the context doesn't contain enough information, say so clearly.\n"
    "- Respond in the same language as the user's question.\n"
    "- Be concise and practical — users are busy production staff.\n"
    "- When referencing orders or data, cite specifics (order numbers, quantities, etc.).\n"
    "{factory_context}"
    "\n\nRELEVANT DATA FROM DATABASE:\n{rag_context}"
)


def _build_system_prompt(
    rag_context: str,
    factory_names: Optional[list[str]] = None,
) -> str:
    """Build system prompt with RAG context and factory info."""
    factory_context = ""
    if factory_names:
        factory_context = (
            f"\nThe user works at: {', '.join(factory_names)}. "
            "Prioritize information relevant to their factories.\n"
        )
    return SYSTEM_PROMPT_TEMPLATE.format(
        factory_context=factory_context,
        rag_context=rag_context if rag_context else "No relevant data found.",
    )


def _build_messages(
    conversation_history: list[dict],
    user_message: str,
) -> list[dict]:
    """Build message list from conversation history + current message."""
    messages = []
    # Include recent history (trimmed to MAX_HISTORY_MESSAGES)
    recent = conversation_history[-MAX_HISTORY_MESSAGES:]
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    return messages


async def _call_anthropic(
    system_prompt: str,
    messages: list[dict],
    api_key: str,
) -> str:
    """Call Anthropic Claude API."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": messages,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # Claude API returns content as a list of blocks
        content_blocks = data.get("content", [])
        text_parts = [
            block["text"]
            for block in content_blocks
            if block.get("type") == "text"
        ]
        return "\n".join(text_parts) if text_parts else ""


async def _call_openai(
    system_prompt: str,
    messages: list[dict],
    api_key: str,
) -> str:
    """Call OpenAI Chat Completions API."""
    openai_messages = [{"role": "system", "content": system_prompt}] + messages
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": openai_messages,
                "max_tokens": 1024,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def _fallback_response(rag_context: str) -> str:
    """Generate a rule-based response when no LLM API is available."""
    if not rag_context or rag_context.strip() == "":
        return (
            "AI chat requires API key configuration. "
            "Please set ANTHROPIC_API_KEY or OPENAI_API_KEY in the environment. "
            "RAG search found no relevant data for your query."
        )
    return (
        "AI chat requires API key configuration. "
        "Please set ANTHROPIC_API_KEY or OPENAI_API_KEY in the environment.\n\n"
        "However, here is relevant data from the database:\n\n"
        f"{rag_context}"
    )


async def generate_response(
    user_message: str,
    context: list[dict],
    conversation_history: list[dict],
    factory_names: Optional[list[str]] = None,
) -> tuple[str, str]:
    """
    Generate AI response using available LLM.

    Priority:
    1. ANTHROPIC_API_KEY → Claude API
    2. OPENAI_API_KEY → OpenAI API
    3. Fallback → return RAG context as-is with config message

    Returns:
        Tuple of (response_text, provider_used)
    """
    settings = get_settings()

    # Build RAG context string
    rag_context = "\n\n".join(
        f"[{item.get('source_table', 'unknown')}] {item.get('content_text', '')}"
        for item in context
    ) if context else ""

    system_prompt = _build_system_prompt(rag_context, factory_names)
    messages = _build_messages(conversation_history, user_message)

    # Try Anthropic first
    if settings.ANTHROPIC_API_KEY:
        try:
            text = await _call_anthropic(
                system_prompt, messages, settings.ANTHROPIC_API_KEY,
            )
            return text, "anthropic"
        except Exception as e:
            logger.warning("Anthropic API call failed: %s", e)

    # Try OpenAI
    if settings.OPENAI_API_KEY:
        try:
            text = await _call_openai(
                system_prompt, messages, settings.OPENAI_API_KEY,
            )
            return text, "openai"
        except Exception as e:
            logger.warning("OpenAI API call failed: %s", e)

    # Fallback
    return _fallback_response(rag_context), "fallback"
