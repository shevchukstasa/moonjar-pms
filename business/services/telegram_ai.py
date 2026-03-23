"""
AI-powered enhancements for Telegram bot.
Uses Claude/OpenAI for smart features beyond rule-based logic.

All functions are safe to call without API keys — they return None/fallback
so the bot works 100% without AI configuration.

Priority: Anthropic Claude -> OpenAI -> None (graceful degradation).
"""

import logging
import json
import re
import time
from typing import Optional

import httpx

from api.config import get_settings

logger = logging.getLogger("moonjar.telegram_ai")

# Cost monitoring: track calls per session
_ai_call_counts: dict[str, int] = {}
_ai_call_start = time.time()

# Maximum response length for Telegram messages
MAX_TELEGRAM_CHARS = 500


# ────────────────────────────────────────────────────────────────
# Core LLM call (shared by all features)
# ────────────────────────────────────────────────────────────────

async def _call_llm(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 512,
    temperature: float = 0.3,
) -> Optional[str]:
    """
    Call LLM with Anthropic-first, OpenAI-fallback strategy.

    Returns the response text or None if no API is available / call fails.
    All exceptions are caught — this NEVER raises.
    """
    settings = get_settings()

    # Try Anthropic first
    if settings.ANTHROPIC_API_KEY:
        try:
            result = await _call_anthropic(
                system_prompt, user_message,
                settings.ANTHROPIC_API_KEY,
                max_tokens, temperature,
            )
            _track_call("anthropic")
            return result
        except Exception as e:
            logger.warning("telegram_ai: Anthropic call failed: %s", e)

    # Try OpenAI
    if settings.OPENAI_API_KEY:
        try:
            result = await _call_openai(
                system_prompt, user_message,
                settings.OPENAI_API_KEY,
                max_tokens, temperature,
            )
            _track_call("openai")
            return result
        except Exception as e:
            logger.warning("telegram_ai: OpenAI call failed: %s", e)

    logger.debug("telegram_ai: no API keys configured, skipping AI call")
    return None


async def _call_anthropic(
    system_prompt: str,
    user_message: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call Anthropic Claude API (Haiku for speed/cost)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-20250514",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        content_blocks = data.get("content", [])
        text_parts = [
            block["text"]
            for block in content_blocks
            if block.get("type") == "text"
        ]
        return "\n".join(text_parts) if text_parts else ""


async def _call_openai(
    system_prompt: str,
    user_message: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call OpenAI Chat Completions API (gpt-4o-mini for speed/cost)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def _track_call(provider: str) -> None:
    """Track AI call for cost monitoring."""
    key = f"{provider}"
    _ai_call_counts[key] = _ai_call_counts.get(key, 0) + 1
    total = sum(_ai_call_counts.values())
    if total % 50 == 0:
        elapsed_h = (time.time() - _ai_call_start) / 3600
        logger.info(
            "telegram_ai usage: %d total calls (%.1f hours). Breakdown: %s",
            total, elapsed_h, _ai_call_counts,
        )


def _truncate(text: str, max_len: int = MAX_TELEGRAM_CHARS) -> str:
    """Truncate text to fit Telegram message limits."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


# ────────────────────────────────────────────────────────────────
# Feature 1: Natural Language Command Parser
# ────────────────────────────────────────────────────────────────

_NL_SYSTEM_PROMPT = """You are a command parser for Moonjar PMS, a stone production management system.
Parse the user's free-text message into a structured JSON command.

Available commands:
- {"command": "defect", "position": "<pos_ref>", "value": <percent>} — report defect percentage
- {"command": "actual", "position": "<pos_ref>", "value": <quantity>} — record actual output
- {"command": "status"} — show pending tasks
- {"command": "plan"} — show tomorrow's plan
- {"command": "recipe", "query": "<search term>"} — search for a recipe
- {"command": "help"} — show help

Rules:
- Return ONLY valid JSON, no markdown, no explanation.
- If the text is casual conversation, greeting, or not a command, return: null
- Position references can be numbers like "123", "#123", "POS-123".
- Understand Indonesian, English, and Russian.
- "дефект", "cacat", "defect" all mean defect command.
- "план", "rencana", "plan" all mean plan command.
- "статус", "status", "tugas" all mean status command.
- "рецепт", "resep", "recipe" all mean recipe command.
- "помощь", "bantuan", "help" all mean help command.
- "факт", "aktual", "actual", "output" all mean actual command."""


async def parse_natural_language(text: str, user_context: dict) -> Optional[dict]:
    """
    Parse free-text messages into structured commands.

    Examples:
    - "defect pada posisi 123 sebesar 5 persen" -> {"command": "defect", "position": "123", "value": 5}
    - "покажи план на завтра" -> {"command": "plan"}
    - "какой рецепт у Moss Glaze?" -> {"command": "recipe", "query": "Moss Glaze"}

    Returns None if text is not a command (just conversation).
    """
    try:
        # Quick heuristic: skip very short or obvious non-commands
        stripped = text.strip()
        if len(stripped) < 3:
            return None

        # Build context string
        ctx = ""
        if user_context.get("user_name"):
            ctx += f"User: {user_context['user_name']}. "
        if user_context.get("role"):
            ctx += f"Role: {user_context['role']}. "

        user_msg = f"Parse this message into a command:\n\n{stripped}"
        if ctx:
            user_msg = f"Context: {ctx}\n\n{user_msg}"

        result = await _call_llm(
            _NL_SYSTEM_PROMPT,
            user_msg,
            max_tokens=200,
            temperature=0.1,
        )

        if not result:
            return None

        # Clean up response — strip markdown code blocks if present
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```\w*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)
        cleaned = cleaned.strip()

        if cleaned.lower() == "null" or not cleaned:
            return None

        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "command" in parsed:
            logger.info("NL parsed: '%s' -> %s", stripped[:50], parsed)
            return parsed
        return None

    except (json.JSONDecodeError, Exception) as e:
        logger.debug("NL parse failed for '%s': %s", text[:50], e)
        return None


# ────────────────────────────────────────────────────────────────
# Feature 2: Smart Daily Message
# ────────────────────────────────────────────────────────────────

_DAILY_SYSTEM_PROMPT = """You are a production assistant for Moonjar, a stone products manufacturer in Bali/Java.
Generate a brief, natural-language summary to APPEND to the daily task distribution message.

Guidelines:
- Keep it under 400 characters.
- Use the specified language (id=Indonesian, en=English, ru=Russian).
- Highlight the most important insight: priorities, bottlenecks, warnings.
- Be practical and action-oriented.
- No greetings or sign-offs — just the insight.
- Use simple language that factory workers understand."""


async def generate_smart_daily_message(
    factory_name: str,
    glazing_tasks: list[dict],
    kiln_tasks: list[dict],
    sorting_tasks: list[dict],
    kpi_data: dict,
    language: str = "id",
) -> Optional[str]:
    """
    Generate an intelligent daily task summary insight.

    Returns a short natural-language paragraph to append to the standard
    daily message, or None if AI is unavailable.
    """
    try:
        # Build data summary for the LLM
        glazing_count = len(glazing_tasks)
        kiln_count = len(kiln_tasks)
        sorting_count = len(sorting_tasks)

        urgent_glazing = sum(1 for t in glazing_tasks if t.get("behind_schedule"))
        urgent_kiln = sum(1 for t in kiln_tasks if t.get("behind_schedule"))

        defect_rate = kpi_data.get("defect_rate", 0)
        prev_defect = kpi_data.get("prev_defect_rate", 0)
        throughput = kpi_data.get("throughput", 0)

        # Deadlines
        deadlines = []
        for t in glazing_tasks[:5]:
            if t.get("deadline"):
                deadlines.append(f"Order #{t.get('order_number', '?')}: deadline {t['deadline']}")

        data_summary = (
            f"Factory: {factory_name}\n"
            f"Glazing tasks: {glazing_count} (urgent: {urgent_glazing})\n"
            f"Kiln tasks: {kiln_count} (urgent: {urgent_kiln})\n"
            f"Sorting tasks: {sorting_count}\n"
            f"Yesterday's defect rate: {defect_rate:.1f}% (previous: {prev_defect:.1f}%)\n"
            f"Throughput: {throughput} pcs\n"
        )
        if deadlines:
            data_summary += "Upcoming deadlines:\n" + "\n".join(deadlines[:3]) + "\n"

        user_msg = (
            f"Language: {language}\n"
            f"Data:\n{data_summary}\n"
            f"Generate a brief insight/recommendation for the production team."
        )

        result = await _call_llm(
            _DAILY_SYSTEM_PROMPT,
            user_msg,
            max_tokens=300,
            temperature=0.4,
        )

        if result:
            return _truncate(result.strip(), 400)
        return None

    except Exception as e:
        logger.warning("Smart daily message generation failed: %s", e)
        return None


# ────────────────────────────────────────────────────────────────
# Feature 3: Defect Diagnostics
# ────────────────────────────────────────────────────────────────

_DEFECT_SYSTEM_PROMPT = """You are a ceramics production quality expert at Moonjar, a stone tile manufacturer.
Analyze a defect report and suggest possible root causes.

Guidelines:
- Keep response under 400 characters.
- Be specific and actionable.
- Consider: glaze recipe, kiln temperature/duration, raw materials, weather, operator error.
- If you see patterns in recent defects (same kiln, same recipe), highlight them.
- Respond in the same language as the data provided (Indonesian/English/Russian).
- No greetings — just the analysis."""


async def diagnose_defect(
    position_info: dict,
    defect_percent: float,
    recent_defects: list[dict],
    kiln_history: list[dict],
) -> Optional[str]:
    """
    AI-powered root cause analysis for defects.

    Returns suggestions like:
    - "Similar defect pattern seen 3 days ago on same recipe - check glaze consistency"
    - "Kiln #2 has had 3 high-defect batches this week - inspect heating elements"

    Returns None if AI is unavailable.
    """
    try:
        # Build context
        pos_color = position_info.get("color", "unknown")
        pos_size = position_info.get("size", "unknown")
        pos_recipe = position_info.get("recipe_name", "unknown")
        pos_kiln = position_info.get("kiln_name", "unknown")

        # Recent defects summary
        recent_lines = []
        for d in recent_defects[:5]:
            recent_lines.append(
                f"- {d.get('date', '?')}: {d.get('defect_pct', 0):.1f}% "
                f"on {d.get('recipe', '?')} in {d.get('kiln', '?')}"
            )

        # Kiln history summary
        kiln_lines = []
        for k in kiln_history[:5]:
            kiln_lines.append(
                f"- {k.get('date', '?')}: {k.get('kiln_name', '?')} "
                f"{k.get('temperature', '?')}C, defect {k.get('defect_pct', 0):.1f}%"
            )

        user_msg = (
            f"Current defect: {defect_percent:.1f}%\n"
            f"Position: color={pos_color}, size={pos_size}, recipe={pos_recipe}, kiln={pos_kiln}\n\n"
            f"Recent defects on same recipe/kiln:\n"
            + ("\n".join(recent_lines) if recent_lines else "No recent data") +
            f"\n\nKiln recent history:\n"
            + ("\n".join(kiln_lines) if kiln_lines else "No recent data")
        )

        result = await _call_llm(
            _DEFECT_SYSTEM_PROMPT,
            user_msg,
            max_tokens=300,
            temperature=0.3,
        )

        if result:
            return _truncate(result.strip(), 400)
        return None

    except Exception as e:
        logger.warning("Defect diagnosis failed: %s", e)
        return None


# ────────────────────────────────────────────────────────────────
# Feature 4: Smart Task Prioritization
# ────────────────────────────────────────────────────────────────

_PRIORITY_SYSTEM_PROMPT = """You are a production scheduling assistant for Moonjar, a stone products manufacturer.
Recommend task execution order based on constraints.

Guidelines:
- Keep response under 400 characters.
- Consider: deadlines, kiln availability, material dependencies, batch efficiency.
- Prioritize: urgent deadlines > kiln-ready items > items behind schedule.
- Be practical — factory workers need clear, simple advice.
- Respond in Indonesian by default (unless data suggests otherwise).
- No greetings — just the recommendation."""


async def prioritize_tasks(
    tasks: list[dict],
    kiln_schedule: list[dict],
    material_stock: dict,
) -> Optional[str]:
    """
    AI recommends task order based on constraints.

    Returns: Natural language advice on what to do first and why.
    Returns None if AI is unavailable.
    """
    try:
        if not tasks:
            return None

        # Build compact task summary
        task_lines = []
        for t in tasks[:10]:
            deadline = t.get("deadline", "no deadline")
            status = t.get("status", "pending")
            desc = t.get("description", t.get("type", "task"))[:40]
            order = t.get("order_number", "?")
            task_lines.append(
                f"- Order #{order}: {desc} [{status}] deadline={deadline}"
            )

        # Kiln availability
        kiln_lines = []
        for k in kiln_schedule[:5]:
            kiln_lines.append(
                f"- {k.get('kiln_name', '?')}: available {k.get('available_at', '?')}"
            )

        # Low stock warnings
        low_stock = []
        for mat_name, stock_info in (material_stock or {}).items():
            if isinstance(stock_info, dict) and stock_info.get("low"):
                low_stock.append(f"- {mat_name}: {stock_info.get('quantity', 0)} {stock_info.get('unit', '')}")

        user_msg = (
            f"Tasks ({len(tasks)}):\n" + "\n".join(task_lines) +
            f"\n\nKiln schedule:\n" + ("\n".join(kiln_lines) if kiln_lines else "No data") +
            f"\n\nLow stock materials:\n" + ("\n".join(low_stock) if low_stock else "All OK")
        )

        result = await _call_llm(
            _PRIORITY_SYSTEM_PROMPT,
            user_msg,
            max_tokens=300,
            temperature=0.3,
        )

        if result:
            return _truncate(result.strip(), 400)
        return None

    except Exception as e:
        logger.warning("Task prioritization failed: %s", e)
        return None


# ────────────────────────────────────────────────────────────────
# Feature 5: Language Detection & Response
# ────────────────────────────────────────────────────────────────

# Common words for heuristic detection
_RUSSIAN_MARKERS = set("абвгдежзийклмнопрстуфхцчшщъыьэюя")
_INDONESIAN_WORDS = {
    "dan", "yang", "di", "ke", "dari", "untuk", "ini", "itu",
    "dengan", "pada", "tidak", "ada", "juga", "sudah", "akan",
    "bisa", "atau", "saya", "anda", "kami", "mereka", "kalau",
    "sudah", "belum", "silakan", "tolong", "terima", "kasih",
    "apa", "siapa", "dimana", "kapan", "mengapa", "bagaimana",
    "posisi", "tugas", "glasir", "tungku", "cacat", "resep",
    "pabrik", "perintah", "bantuan", "rencana", "kirim",
}


def detect_language(text: str) -> str:
    """
    Detect language from text. Returns 'id', 'en', or 'ru'.

    Uses a simple heuristic:
    1. If text contains Cyrillic characters -> 'ru'
    2. If text contains common Indonesian words -> 'id'
    3. Default -> 'en'
    """
    if not text:
        return "en"

    lower = text.lower()

    # Check for Cyrillic characters
    cyrillic_count = sum(1 for c in lower if c in _RUSSIAN_MARKERS)
    if cyrillic_count > len(lower) * 0.15:
        return "ru"

    # Check for Indonesian words
    words = set(re.split(r'\s+', lower))
    indo_matches = words & _INDONESIAN_WORDS
    if len(indo_matches) >= 2 or (len(indo_matches) >= 1 and len(words) <= 3):
        return "id"

    return "en"


async def translate_response(text: str, target_lang: str) -> str:
    """
    Translate bot response to target language if needed.

    Falls back to returning original text if AI is unavailable.
    """
    if not text or target_lang == "en":
        return text

    try:
        lang_name = {"id": "Indonesian", "ru": "Russian"}.get(target_lang, "English")

        result = await _call_llm(
            f"Translate the following text to {lang_name}. "
            f"Keep technical terms (order numbers, position IDs) unchanged. "
            f"Return ONLY the translation, nothing else.",
            text,
            max_tokens=400,
            temperature=0.2,
        )

        if result:
            return _truncate(result.strip())
        return text  # Fallback to original

    except Exception as e:
        logger.debug("Translation failed: %s", e)
        return text


# ────────────────────────────────────────────────────────────────
# Feature 6: Material Matching with LLM Fallback
# ────────────────────────────────────────────────────────────────

_MATERIAL_SYSTEM_PROMPT = """You are a materials expert for a ceramics/stone tile manufacturer (Moonjar).
Match a delivery note material name to the best candidate from the database.

You understand:
- Chemical synonyms: "sodium carbonate" = "soda ash" = "Na2CO3"
- Brand names: "Tomat" is a brand of frit, "Ferro" is a brand of pigments
- Abbreviations: "CMC" = "Carboxymethyl Cellulose", "RHA" = "Rice Husk Ash"
- Indonesian material names: "Kaolin putih" = "White Kaolin"
- Size formats: "10/10" = "10x10"

Return ONLY a JSON object:
{"match_index": <0-based index of best candidate or null>, "confidence": <0.0-1.0>, "reason": "<brief explanation>"}

If none of the candidates match, return: {"match_index": null, "confidence": 0.0, "reason": "No match found"}"""


async def ai_match_material(
    delivery_name: str,
    top_candidates: list[dict],
    context: str = "",
) -> Optional[dict]:
    """
    When fuzzy matcher confidence is low (0.3-0.5), use LLM to decide.

    Args:
        delivery_name: Material name from delivery note.
        top_candidates: Top candidates from material_matcher, each with
                        keys: material_id, material_name, score.
        context: Additional context (supplier name, delivery note text).

    Returns:
        Dict with keys: material_id, material_name, confidence, reason.
        Or None if AI is unavailable or no match found.
    """
    try:
        if not top_candidates:
            return None

        # Build candidates list
        candidate_lines = []
        for i, c in enumerate(top_candidates):
            candidate_lines.append(
                f"{i}. \"{c['material_name']}\" (fuzzy score: {c.get('score', 0):.2f})"
            )

        user_msg = (
            f"Delivery note material: \"{delivery_name}\"\n"
            + (f"Context: {context}\n" if context else "")
            + f"\nCandidates from database:\n"
            + "\n".join(candidate_lines)
        )

        result = await _call_llm(
            _MATERIAL_SYSTEM_PROMPT,
            user_msg,
            max_tokens=200,
            temperature=0.1,
        )

        if not result:
            return None

        # Parse JSON response
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```\w*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)
        match_idx = parsed.get("match_index")
        confidence = parsed.get("confidence", 0.0)
        reason = parsed.get("reason", "")

        if match_idx is not None and 0 <= match_idx < len(top_candidates):
            candidate = top_candidates[match_idx]
            logger.info(
                "AI material match: '%s' -> '%s' (confidence=%.2f, reason=%s)",
                delivery_name, candidate["material_name"], confidence, reason,
            )
            return {
                "material_id": candidate["material_id"],
                "material_name": candidate["material_name"],
                "confidence": confidence,
                "reason": reason,
            }

        logger.debug("AI material match: no match for '%s'", delivery_name)
        return None

    except (json.JSONDecodeError, Exception) as e:
        logger.debug("AI material match failed for '%s': %s", delivery_name, e)
        return None
