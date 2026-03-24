"""
LLM Photo Analysis Service.

Uses Claude Vision API to analyze production photos:
- Scale photos: read weight value, verify pigment color
- Quality photos: identify defects, cracks, color mismatches
- Packing photos: verify label correctness

Graceful fallback: if no API key -> log warning, return None.
"""

import base64
import json
import logging
import os
import re
from typing import Optional

import httpx

logger = logging.getLogger("moonjar.photo_analysis")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_VISION_MODEL_OCR = "gpt-4.1-nano"    # Cheap OCR for delivery/scale/packing (~$0.10/1M)
OPENAI_VISION_MODEL_QUALITY = "gpt-4.1"    # Smart analysis for quality/defect (~$2.00/1M)

# Types that prefer cheap OpenAI model (OCR/document reading)
_CHEAP_VISION_TYPES = {"delivery", "scale", "packing"}
# Types that prefer Claude (complex visual analysis)
_SMART_VISION_TYPES = {"quality", "defect"}

# ── Prompts per analysis type ────────────────────────────────────────────

_SCALE_PROMPT = (
    "You are analyzing a production scale photo from a stone/ceramic tile factory. "
    "Read the weight shown on the scale display. Also identify the material "
    "color/type if visible in the photo.\n\n"
    "Return ONLY valid JSON (no markdown, no code fences):\n"
    '{"weight_kg": <number or null>, "unit": "kg", '
    '"pigment_color": "<color description or null>"}'
)

_QUALITY_PROMPT = (
    "You are a quality inspector analyzing a ceramic tile/stone product photo. "
    "Look carefully for: cracks, glaze defects, color inconsistencies, surface "
    "damage, chipping, warping, or any visual defects.\n\n"
    "Return ONLY valid JSON (no markdown, no code fences):\n"
    '{"defects_found": [{"type": "<defect type>", "severity": "low|medium|high", '
    '"location": "<where on the product>"}], '
    '"overall_quality": "pass|fail|needs_review", '
    '"description": "<brief description>"}'
)

_PACKING_PROMPT = (
    "You are checking a packing label photo from a stone product factory. "
    "Read all text visible on the label: order number, quantity, size, color, "
    "any other identifiers.\n\n"
    "Return ONLY valid JSON (no markdown, no code fences):\n"
    '{"order_number": "<string or null>", "quantity": <number or null>, '
    '"size": "<string or null>", "color": "<string or null>", '
    '"other_text": "<any other visible text>"}'
)

_DELIVERY_PROMPT = (
    "You are analyzing a delivery note (surat jalan / накладная) photo from a stone/ceramic "
    "factory. Read ALL information visible on the document.\n\n"
    "Extract:\n"
    "- Supplier name\n"
    "- Delivery date\n"
    "- Document/reference number\n"
    "- List of items: material name, quantity, unit (kg/pcs/bags/liters)\n"
    "- Any notes or remarks\n\n"
    "Return ONLY valid JSON (no markdown, no code fences):\n"
    '{"supplier": "<name or null>", "delivery_date": "<YYYY-MM-DD or null>", '
    '"reference_number": "<string or null>", '
    '"items": [{"material_name": "<name>", "quantity": <number>, "unit": "<unit>"}], '
    '"notes": "<any additional text>"}'
)

PROMPTS = {
    "scale": _SCALE_PROMPT,
    "quality": _QUALITY_PROMPT,
    "packing": _PACKING_PROMPT,
    "delivery": _DELIVERY_PROMPT,
}


def _build_system_prompt(analysis_type: str, context: dict | None) -> str:
    """Build a system prompt with optional position context."""
    base = PROMPTS.get(analysis_type, PROMPTS["quality"])
    if context:
        ctx_parts = []
        if context.get("position"):
            ctx_parts.append(f"Position reference: {context['position']}")
        if context.get("expected_weight"):
            ctx_parts.append(f"Expected weight: {context['expected_weight']} kg")
        if context.get("expected_color"):
            ctx_parts.append(f"Expected color: {context['expected_color']}")
        if ctx_parts:
            base += "\n\nContext from production system:\n" + "\n".join(ctx_parts)
    return base


def _parse_llm_json(raw_text: str) -> dict:
    """Extract JSON from LLM response, stripping markdown fences if present."""
    text = raw_text.strip()
    # Strip ```json ... ``` fences
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}


async def _call_openai_vision(system_prompt: str, b64_image: str, media_type: str, api_key: str, model: str | None = None) -> str | None:
    """Call OpenAI Vision API. Model selected by caller based on task complexity."""
    use_model = model or OPENAI_VISION_MODEL_OCR
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": use_model,
                    "max_tokens": 1024,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{media_type};base64,{b64_image}",
                                        "detail": "high",
                                    },
                                },
                                {"type": "text", "text": "Analyze this photo and return the JSON result."},
                            ],
                        },
                    ],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("OpenAI Vision call failed: %s", e)
        return None


async def _call_claude_vision(system_prompt: str, b64_image: str, media_type: str, api_key: str) -> str | None:
    """Call Claude Vision API with prompt caching."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 1024,
                    "system": [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64_image}},
                            {"type": "text", "text": "Analyze this photo and return the JSON result."},
                        ],
                    }],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            content_blocks = data.get("content", [])
            return "\n".join(b["text"] for b in content_blocks if b.get("type") == "text") or None
    except Exception as e:
        logger.warning("Claude Vision call failed: %s", e)
        return None


async def analyze_photo(
    image_bytes: bytes,
    analysis_type: str = "scale",
    context: dict | None = None,
) -> dict | None:
    """
    Analyze a photo using the best Vision API for the task.

    Auto-selects model:
    - delivery/scale/packing → GPT-4o-mini (cheap OCR, ~$0.001/photo)
    - quality/defect → Claude Sonnet (smart analysis, ~$0.006/photo)
    - Fallback: tries the other provider if primary fails

    Returns:
        {"analysis_type", "readings", "confidence", "issues", "raw_description"}
        or None if no API key available.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not openai_key and not anthropic_key:
        logger.warning("No Vision API key set (OPENAI_API_KEY or ANTHROPIC_API_KEY) — photo analysis skipped")
        return None

    if analysis_type not in PROMPTS:
        logger.warning(f"Unknown analysis_type '{analysis_type}', falling back to 'quality'")
        analysis_type = "quality"

    # Encode image
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Detect media type
    media_type = "image/jpeg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        media_type = "image/png"
    elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        media_type = "image/webp"

    system_prompt = _build_system_prompt(analysis_type, context)

    # Smart model selection: cheap nano for OCR, gpt-4.1 for quality analysis
    raw_text = None
    provider = None

    if analysis_type in _CHEAP_VISION_TYPES and openai_key:
        # gpt-4.1-nano for OCR tasks (delivery/scale/packing) — $0.10/1M tokens
        raw_text = await _call_openai_vision(system_prompt, b64_image, media_type, openai_key, model=OPENAI_VISION_MODEL_OCR)
        provider = "openai-nano"

    if not raw_text and analysis_type in _SMART_VISION_TYPES and openai_key:
        # gpt-4.1 for quality/defect analysis — $2.00/1M tokens (was Claude $3.00)
        raw_text = await _call_openai_vision(system_prompt, b64_image, media_type, openai_key, model=OPENAI_VISION_MODEL_QUALITY)
        provider = "openai-4.1"

    if not raw_text and anthropic_key:
        # Fallback to Claude if OpenAI fails
        raw_text = await _call_claude_vision(system_prompt, b64_image, media_type, anthropic_key)
        provider = "anthropic"

    if not raw_text and openai_key and provider != "openai":
        # Last resort: try OpenAI if Claude failed
        raw_text = await _call_openai_vision(system_prompt, b64_image, media_type, openai_key)
        provider = "openai"

    if not raw_text:
        logger.warning("All Vision APIs failed for %s analysis", analysis_type)
        return None

    logger.info("Photo analysis via %s (%s): success", provider, analysis_type)

    # Parse structured data from response
    readings = _parse_llm_json(raw_text)

    # Build result
    result = {
        "analysis_type": analysis_type,
        "readings": readings,
        "confidence": 0.9 if readings else 0.0,
        "issues": [],
        "raw_description": raw_text,
    }

    # Detect issues based on analysis type
    if analysis_type == "scale":
        if not readings.get("weight_kg"):
            result["issues"].append("Could not read weight from scale display")
            result["confidence"] = 0.3
    elif analysis_type == "quality":
        defects = readings.get("defects_found", [])
        if defects:
            result["issues"] = [
                f"{d.get('type', 'unknown')} ({d.get('severity', '?')})"
                for d in defects
            ]
            if readings.get("overall_quality") == "fail":
                result["confidence"] = 0.95
    elif analysis_type == "packing":
        if not readings.get("order_number"):
            result["issues"].append("Could not read order number from label")
            result["confidence"] = 0.5
    elif analysis_type == "delivery":
        items = readings.get("items", [])
        if not items:
            result["issues"].append("Could not read any items from delivery note")
            result["confidence"] = 0.3
        else:
            result["confidence"] = 0.85
        if not readings.get("supplier"):
            result["issues"].append("Could not read supplier name")

    logger.info(
        "Photo analysis complete: type=%s, confidence=%s, issues=%d",
        analysis_type, result["confidence"], len(result["issues"]),
    )
    return result


def format_analysis_message(result: dict, position_ref: str | None = None) -> str:
    """
    Format analysis result as a Telegram message in Indonesian (Bahasa).
    """
    atype = result.get("analysis_type", "unknown")
    readings = result.get("readings", {})
    issues = result.get("issues", [])

    lines = ["Analisis foto:"]

    if atype == "scale":
        weight = readings.get("weight_kg")
        color = readings.get("pigment_color")
        unit = readings.get("unit", "kg")
        if weight is not None:
            lines.append(f"Berat: {weight} {unit}")
        else:
            lines.append("Berat: tidak terbaca")
        if color:
            lines.append(f"Warna: {color}")

    elif atype == "quality":
        quality = readings.get("overall_quality", "?")
        quality_labels = {
            "pass": "Lulus",
            "fail": "Gagal",
            "needs_review": "Perlu Review",
        }
        lines.append(f"Kualitas: {quality_labels.get(quality, quality)}")
        defects = readings.get("defects_found", [])
        if defects:
            lines.append(f"Cacat ditemukan: {len(defects)}")
            for d in defects[:3]:  # max 3 defects in message
                severity = d.get("severity", "?")
                dtype = d.get("type", "?")
                lines.append(f"  - {dtype} ({severity})")
        desc = readings.get("description")
        if desc:
            lines.append(f"Deskripsi: {desc}")

    elif atype == "packing":
        order = readings.get("order_number")
        qty = readings.get("quantity")
        size = readings.get("size")
        color = readings.get("color")
        if order:
            lines.append(f"No. Order: {order}")
        if qty:
            lines.append(f"Jumlah: {qty}")
        if size:
            lines.append(f"Ukuran: {size}")
        if color:
            lines.append(f"Warna: {color}")

    if issues:
        lines.append(f"\nPeringatan: {', '.join(issues)}")

    if position_ref:
        lines.append(f"\nTersimpan untuk posisi {position_ref}")

    return "\n".join(lines)


def format_delivery_message(
    result: dict,
    matched_items: list[dict] | None = None,
    unmatched_items: list[dict] | None = None,
) -> str:
    """
    Format delivery analysis result as a Telegram message in Indonesian (Bahasa).

    Args:
        result: Analysis result from analyze_photo(analysis_type="delivery").
        matched_items: List of dicts with keys: material_name, quantity, unit, new_balance, material_db_name.
        unmatched_items: List of dicts with keys: material_name, quantity, unit.

    Returns:
        Formatted message string.
    """
    readings = result.get("readings", {})
    supplier = readings.get("supplier") or "Tidak diketahui"
    delivery_date = readings.get("delivery_date") or "Tidak diketahui"
    reference = readings.get("reference_number") or "-"
    notes = readings.get("notes") or ""

    lines = [
        f"Penerimaan Material — {delivery_date}",
        f"Pemasok: {supplier}",
        f"No. Ref: {reference}",
        "",
    ]

    total_received = 0

    if matched_items:
        for item in matched_items:
            lines.append(
                f"  {item['material_name']}: +{item['quantity']} {item['unit']} "
                f"(stok: {item.get('new_balance', '?')})"
            )
            total_received += 1

    if unmatched_items:
        for item in unmatched_items:
            lines.append(
                f"  {item['material_name']}: +{item['quantity']} {item['unit']} — "
                f"tidak ditemukan di database"
            )

    lines.append("")
    lines.append(f"Total: {total_received} item diterima")

    if unmatched_items:
        lines.append(f"{len(unmatched_items)} item tidak ditemukan di database")

    if notes:
        lines.append(f"\nCatatan: {notes}")

    issues = result.get("issues", [])
    if issues:
        lines.append(f"\nPeringatan: {', '.join(issues)}")

    return "\n".join(lines)
