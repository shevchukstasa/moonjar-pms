"""
Kiln Rotation Rules Service.

Rules:
- Each factory can define a default glaze sequence for all kilns
- Individual kilns can override with their own sequence
- Incompatible pairs define glazes that need cooldown between them
- When forming a batch, check if the proposed glaze follows rotation rules
- If violation: warn PM, suggest reorder, or block (configurable)

The glaze type for a batch is derived from the cofiring_key stored
in batch.metadata_json (e.g. "standard", "two_stage:gold").
"""

import logging
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from api.models import KilnRotationRule, Batch, Resource
from api.enums import BatchStatus

logger = logging.getLogger("moonjar.rotation_rules")


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def _get_last_fired_glaze(db: Session, kiln_id: UUID) -> Optional[str]:
    """
    Determine the glaze type of the last completed batch in a kiln.

    Uses batch.metadata_json.cofiring_group if available,
    otherwise falls back to the cofiring_key derived from positions.
    """
    last_batch = (
        db.query(Batch)
        .filter(
            Batch.resource_id == kiln_id,
            Batch.status == BatchStatus.DONE,
        )
        .order_by(desc(Batch.updated_at))
        .first()
    )
    if not last_batch:
        return None

    meta = last_batch.metadata_json or {}
    # cofiring_group is stored by batch_formation._build_batches_for_group
    glaze = meta.get("cofiring_group")
    if glaze:
        return glaze

    # Fallback: check temperature_group or target_temperature
    if last_batch.target_temperature and last_batch.target_temperature <= 750:
        return "two_stage:gold"

    return "standard"


def _normalize_glaze(glaze_type: str) -> str:
    """Normalize glaze type string for comparison."""
    return (glaze_type or "standard").strip().lower()


# ────────────────────────────────────────────────────────────────
# Core API
# ────────────────────────────────────────────────────────────────

def get_rotation_rule(
    db: Session,
    factory_id: UUID,
    kiln_id: Optional[UUID] = None,
) -> Optional[KilnRotationRule]:
    """
    Get the active rotation rule for a kiln.
    Falls back to factory-wide default (kiln_id IS NULL) if no kiln-specific rule.
    """
    # 1) Try kiln-specific rule
    if kiln_id:
        rule = (
            db.query(KilnRotationRule)
            .filter(
                KilnRotationRule.factory_id == factory_id,
                KilnRotationRule.kiln_id == kiln_id,
                KilnRotationRule.is_active.is_(True),
            )
            .first()
        )
        if rule:
            return rule

    # 2) Fall back to factory default (kiln_id IS NULL)
    rule = (
        db.query(KilnRotationRule)
        .filter(
            KilnRotationRule.factory_id == factory_id,
            KilnRotationRule.kiln_id.is_(None),
            KilnRotationRule.is_active.is_(True),
        )
        .first()
    )
    return rule


def check_rotation_compliance(
    db: Session,
    kiln_id: UUID,
    proposed_glaze_type: str,
    factory_id: UUID,
) -> dict:
    """
    Check if proposed glaze type can follow the last fired glaze in this kiln.

    Returns:
        {
            "compliant": bool,
            "reason": str,
            "cooldown_needed": int,      # minutes of cooldown if incompatible
            "suggestion": str | None,     # recommended next glaze or action
            "last_glaze": str | None,     # what was last fired
        }
    """
    rule = get_rotation_rule(db, factory_id, kiln_id)
    proposed = _normalize_glaze(proposed_glaze_type)

    # No rule configured -> always compliant
    if not rule:
        return {
            "compliant": True,
            "reason": "No rotation rule configured for this kiln/factory.",
            "cooldown_needed": 0,
            "suggestion": None,
            "last_glaze": None,
        }

    last_glaze = _get_last_fired_glaze(db, kiln_id)
    if not last_glaze:
        return {
            "compliant": True,
            "reason": "No previous firing recorded. Any glaze type is allowed.",
            "cooldown_needed": 0,
            "suggestion": None,
            "last_glaze": None,
        }

    last = _normalize_glaze(last_glaze)

    # Check incompatible pairs
    incompatible_pairs = rule.incompatible_pairs or []
    for pair in incompatible_pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        a, b = _normalize_glaze(pair[0]), _normalize_glaze(pair[1])
        if (last == a and proposed == b) or (last == b and proposed == a):
            cooldown = rule.cooldown_minutes or 0
            next_rec = get_next_recommended_glaze(db, kiln_id, factory_id)
            return {
                "compliant": False,
                "reason": (
                    f"Incompatible pair: '{last}' -> '{proposed}'. "
                    f"These glazes cannot follow each other directly."
                ),
                "cooldown_needed": cooldown,
                "suggestion": (
                    f"Recommended next glaze: {next_rec}"
                    if next_rec
                    else f"Wait {cooldown} minutes before firing '{proposed}' after '{last}'."
                ),
                "last_glaze": last,
            }

    # Check sequence order (advisory -- not a hard block)
    sequence = rule.glaze_sequence or []
    if sequence and proposed in [_normalize_glaze(s) for s in sequence]:
        norm_seq = [_normalize_glaze(s) for s in sequence]
        if last in norm_seq:
            last_idx = norm_seq.index(last)
            proposed_idx = norm_seq.index(proposed)
            expected_idx = (last_idx + 1) % len(norm_seq)

            if proposed_idx != expected_idx:
                expected_glaze = sequence[expected_idx]
                return {
                    "compliant": True,  # sequence violation is advisory, not blocking
                    "reason": (
                        f"Sequence advisory: after '{last}', expected '{expected_glaze}' "
                        f"but proposed '{proposed}'. Proceeding is allowed."
                    ),
                    "cooldown_needed": 0,
                    "suggestion": f"Consider firing '{expected_glaze}' next per rotation sequence.",
                    "last_glaze": last,
                }

    return {
        "compliant": True,
        "reason": "Rotation check passed.",
        "cooldown_needed": 0,
        "suggestion": None,
        "last_glaze": last,
    }


def get_next_recommended_glaze(
    db: Session,
    kiln_id: UUID,
    factory_id: UUID,
) -> Optional[str]:
    """Based on last fired glaze and rotation rules, suggest next glaze type."""
    rule = get_rotation_rule(db, factory_id, kiln_id)
    if not rule:
        return None

    sequence = rule.glaze_sequence or []
    if not sequence:
        return None

    last_glaze = _get_last_fired_glaze(db, kiln_id)
    if not last_glaze:
        # No history: recommend first in sequence
        return sequence[0]

    norm_seq = [_normalize_glaze(s) for s in sequence]
    last = _normalize_glaze(last_glaze)

    if last in norm_seq:
        idx = norm_seq.index(last)
        next_idx = (idx + 1) % len(norm_seq)
        return sequence[next_idx]

    # Last glaze not in sequence: recommend first
    return sequence[0]


def validate_batch_rotation(db: Session, batch: Batch) -> dict:
    """
    Check if a batch's proposed firing follows rotation rules for its kiln.

    Returns:
        {
            "compliant": bool,
            "reason": str,
            "cooldown_needed": int,
            "suggestion": str | None,
            "kiln_id": str,
            "batch_id": str,
        }
    """
    if not batch.resource_id or not batch.factory_id:
        return {
            "compliant": True,
            "reason": "Batch has no kiln or factory assigned.",
            "cooldown_needed": 0,
            "suggestion": None,
            "kiln_id": None,
            "batch_id": str(batch.id),
        }

    # Determine proposed glaze from batch metadata
    meta = batch.metadata_json or {}
    proposed_glaze = meta.get("cofiring_group", "standard")

    result = check_rotation_compliance(
        db, batch.resource_id, proposed_glaze, batch.factory_id,
    )
    result["kiln_id"] = str(batch.resource_id)
    result["batch_id"] = str(batch.id)
    return result
