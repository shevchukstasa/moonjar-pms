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


async def analyze_photo(
    image_bytes: bytes,
    analysis_type: str = "scale",
    context: dict | None = None,
) -> dict | None:
    """
    Analyze a photo using Claude Vision API.

    Args:
        image_bytes: Raw image bytes (JPEG/PNG).
        analysis_type: "scale" | "quality" | "packing"
        context: Optional dict with position info, expected weight, etc.

    Returns:
        {
            "analysis_type": "scale",
            "readings": {...},  # parsed JSON from LLM
            "confidence": float,
            "issues": [],
            "raw_description": "..."
        }
        or None if API key missing or call fails.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — photo analysis skipped")
        return None

    if analysis_type not in PROMPTS:
        logger.warning(f"Unknown analysis_type '{analysis_type}', falling back to 'quality'")
        analysis_type = "quality"

    # Encode image
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Detect media type (simple heuristic)
    media_type = "image/jpeg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        media_type = "image/png"
    elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        media_type = "image/webp"

    system_prompt = _build_system_prompt(analysis_type, context)

    # Build Claude Vision API request with prompt caching.
    # System prompt is cached (same per analysis_type) → up to 90% savings
    # on repeated calls of same type within 5-minute TTL.
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "system": [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Analyze this photo and return the JSON result.",
                    },
                ],
            }
        ],
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()

        # Log cache performance
        usage = data.get("usage", {})
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_write = usage.get("cache_creation_input_tokens", 0)
        if cache_read > 0:
            logger.info("Photo analysis cache HIT: %d tokens from cache", cache_read)
        elif cache_write > 0:
            logger.info("Photo analysis cache WRITE: %d tokens cached", cache_write)

        # Extract text from response
        content_blocks = data.get("content", [])
        text_parts = [
            block["text"]
            for block in content_blocks
            if block.get("type") == "text"
        ]
        raw_text = "\n".join(text_parts) if text_parts else ""

        if not raw_text:
            logger.warning("Claude Vision returned empty response")
            return None

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
            f"Photo analysis complete: type={analysis_type}, "
            f"confidence={result['confidence']}, issues={len(result['issues'])}"
        )
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"Claude Vision API HTTP error: {e.response.status_code} — {e.response.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"Photo analysis failed: {e}", exc_info=True)
        return None


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
