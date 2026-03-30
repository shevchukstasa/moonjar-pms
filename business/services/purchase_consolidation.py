"""
Purchase Consolidation Service.

Automatically groups small purchase requests into consolidated orders:
1. Group by supplier + material type
2. Check if any pending PRs for same supplier can be combined
3. If combined quantity reaches min_order_quantity -> create consolidated PR
4. Apply bulk discounts if configured

Rules:
- Only consolidate PRs with status='approved' (not yet sent)
- Same supplier + same material -> combine
- Different materials, same supplier -> combine into one PO
- Max consolidation window: configurable (default 3 days from settings)
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from api.models import (
    MaterialPurchaseRequest,
    PurchaseConsolidationSetting,
    Supplier,
    Material,
)
from api.enums import PurchaseStatus

logger = logging.getLogger("moonjar.purchase_consolidation")

# Default consolidation window if no setting exists for the factory
DEFAULT_CONSOLIDATION_WINDOW_DAYS = 3


def _get_consolidation_window(db: Session, factory_id: UUID) -> int:
    """Return consolidation window in days from factory settings, or default."""
    setting = db.query(PurchaseConsolidationSetting).filter(
        PurchaseConsolidationSetting.factory_id == factory_id,
    ).first()
    if setting:
        return setting.consolidation_window_days
    return DEFAULT_CONSOLIDATION_WINDOW_DAYS


def _get_approved_prs(db: Session, factory_id: UUID) -> list[MaterialPurchaseRequest]:
    """Fetch approved PRs within the consolidation window for a factory."""
    window_days = _get_consolidation_window(db, factory_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    return (
        db.query(MaterialPurchaseRequest)
        .filter(
            MaterialPurchaseRequest.factory_id == factory_id,
            MaterialPurchaseRequest.status == PurchaseStatus.APPROVED.value,
            MaterialPurchaseRequest.created_at >= cutoff,
        )
        .order_by(MaterialPurchaseRequest.created_at.asc())
        .all()
    )


def _extract_materials(pr: MaterialPurchaseRequest) -> list[dict]:
    """Extract material items from PR's materials_json (list or dict format)."""
    mats = pr.materials_json
    if isinstance(mats, list):
        return mats
    if isinstance(mats, dict):
        items = mats.get("items", [])
        if items:
            return items
        # Single-item dict format
        if mats.get("material_id"):
            return [mats]
    return []


def _group_by_supplier(prs: list[MaterialPurchaseRequest]) -> dict[Optional[UUID], list[MaterialPurchaseRequest]]:
    """Group PRs by supplier_id."""
    groups: dict[Optional[UUID], list[MaterialPurchaseRequest]] = defaultdict(list)
    for pr in prs:
        groups[pr.supplier_id].append(pr)
    return dict(groups)


def find_consolidation_candidates(db: Session, factory_id: UUID) -> list[dict]:
    """
    Find approved PRs that can be consolidated.

    Returns list of candidate groups:
    [
      {
        "supplier_id": ...,
        "supplier_name": ...,
        "pr_ids": [...],
        "total_items": N,
        "combined_materials": [...],
      },
      ...
    ]
    """
    prs = _get_approved_prs(db, factory_id)
    if not prs:
        return []

    groups = _group_by_supplier(prs)
    candidates = []

    for supplier_id, group_prs in groups.items():
        # Only suggest consolidation if there are 2+ PRs for the same supplier
        if len(group_prs) < 2:
            continue

        supplier_name = None
        if supplier_id:
            sup = db.query(Supplier).filter(Supplier.id == supplier_id).first()
            supplier_name = sup.name if sup else None

        # Merge materials across all PRs in this group
        combined_materials: dict[str, dict] = {}
        for pr in group_prs:
            for mat_item in _extract_materials(pr):
                mat_id = str(mat_item.get("material_id", ""))
                if not mat_id:
                    continue
                if mat_id in combined_materials:
                    combined_materials[mat_id]["quantity"] += float(mat_item.get("quantity", 0))
                else:
                    combined_materials[mat_id] = {
                        "material_id": mat_id,
                        "material_name": mat_item.get("material_name", mat_item.get("name", "")),
                        "quantity": float(mat_item.get("quantity", 0)),
                        "unit": mat_item.get("unit", ""),
                    }

        candidates.append({
            "supplier_id": str(supplier_id) if supplier_id else None,
            "supplier_name": supplier_name,
            "pr_ids": [str(pr.id) for pr in group_prs],
            "pr_count": len(group_prs),
            "total_items": len(combined_materials),
            "combined_materials": list(combined_materials.values()),
            "earliest_created": min(pr.created_at for pr in group_prs).isoformat() if group_prs else None,
        })

    return candidates


def consolidate_purchase_requests(
    db: Session,
    pr_ids: list[UUID],
    consolidated_by: UUID,
) -> dict:
    """
    Merge multiple PRs into one consolidated PR.

    Steps:
    1. Validate all PRs exist and are in 'approved' status
    2. Validate they share the same supplier and factory
    3. Combine materials_json from all PRs
    4. Create a new consolidated PR
    5. Mark original PRs as 'closed' with consolidation note

    Returns dict with new consolidated PR info.
    """
    if len(pr_ids) < 2:
        raise ValueError("At least 2 purchase requests are required for consolidation")

    # Fetch and validate PRs
    prs = (
        db.query(MaterialPurchaseRequest)
        .filter(MaterialPurchaseRequest.id.in_(pr_ids))
        .all()
    )

    if len(prs) != len(pr_ids):
        found_ids = {str(pr.id) for pr in prs}
        missing = [str(pid) for pid in pr_ids if str(pid) not in found_ids]
        raise ValueError(f"Purchase requests not found: {missing}")

    # All must be 'approved'
    non_approved = [
        str(pr.id) for pr in prs
        if pr.status not in (PurchaseStatus.APPROVED.value, PurchaseStatus.APPROVED)
    ]
    if non_approved:
        raise ValueError(
            f"All PRs must be in 'approved' status. Non-approved: {non_approved}"
        )

    # All must share the same factory
    factory_ids = {pr.factory_id for pr in prs}
    if len(factory_ids) > 1:
        raise ValueError("All PRs must belong to the same factory")
    factory_id = prs[0].factory_id

    # All must share the same supplier (or all be None)
    supplier_ids = {pr.supplier_id for pr in prs}
    if len(supplier_ids) > 1:
        raise ValueError("All PRs must have the same supplier for consolidation")
    supplier_id = prs[0].supplier_id

    # Combine materials
    combined_materials: dict[str, dict] = {}
    all_notes: list[str] = []

    for pr in prs:
        for mat_item in _extract_materials(pr):
            mat_id = str(mat_item.get("material_id", ""))
            if not mat_id:
                continue
            if mat_id in combined_materials:
                combined_materials[mat_id]["quantity"] += float(mat_item.get("quantity", 0))
            else:
                combined_materials[mat_id] = dict(mat_item)
                combined_materials[mat_id]["quantity"] = float(mat_item.get("quantity", 0))

        if pr.notes:
            all_notes.append(f"[PR {str(pr.id)[:8]}] {pr.notes}")

    # Create consolidated PR
    consolidated_note = f"Consolidated from {len(prs)} PRs: {', '.join(str(pr.id)[:8] for pr in prs)}"
    if all_notes:
        consolidated_note += "\n" + "\n".join(all_notes)

    consolidated_pr = MaterialPurchaseRequest(
        factory_id=factory_id,
        supplier_id=supplier_id,
        materials_json=list(combined_materials.values()),
        status=PurchaseStatus.APPROVED,
        source="consolidated",
        approved_by=consolidated_by,
        notes=consolidated_note,
    )
    db.add(consolidated_pr)
    db.flush()  # Get the new ID

    # Close original PRs
    for pr in prs:
        pr.status = PurchaseStatus.CLOSED.value
        pr.notes = (pr.notes or "") + f"\n[Consolidated into PR {str(consolidated_pr.id)[:8]}]"
        pr.updated_at = datetime.now(timezone.utc)

    db.flush()

    logger.info(
        f"Consolidated {len(prs)} PRs into {str(consolidated_pr.id)[:8]} "
        f"(factory={str(factory_id)[:8]}, supplier={str(supplier_id)[:8] if supplier_id else 'N/A'})"
    )

    return {
        "consolidated_pr_id": str(consolidated_pr.id),
        "source_pr_ids": [str(pr.id) for pr in prs],
        "source_count": len(prs),
        "materials_count": len(combined_materials),
        "combined_materials": list(combined_materials.values()),
        "supplier_id": str(supplier_id) if supplier_id else None,
        "factory_id": str(factory_id),
    }


def get_consolidation_suggestions(db: Session, factory_id: UUID) -> list[dict]:
    """
    Return suggestions for consolidation (don't execute, just suggest).

    Wraps find_consolidation_candidates with additional metadata
    like potential savings estimate and urgency.
    """
    candidates = find_consolidation_candidates(db, factory_id)

    suggestions = []
    for group in candidates:
        # Calculate total combined quantity
        total_qty = sum(m.get("quantity", 0) for m in group["combined_materials"])

        suggestions.append({
            **group,
            "total_combined_quantity": round(total_qty, 3),
            "recommendation": (
                "Strongly recommended"
                if group["pr_count"] >= 3
                else "Recommended"
            ),
        })

    # Sort: more PRs first (higher consolidation benefit)
    suggestions.sort(key=lambda s: s["pr_count"], reverse=True)

    return suggestions


def auto_consolidate_on_schedule(db: Session, factory_id: UUID) -> dict:
    """
    Called by scheduler -- auto-consolidate if criteria met.

    Auto-consolidation triggers when:
    - 3+ approved PRs for the same supplier exist within the window
    - OR 2+ PRs that are older than half the consolidation window

    Returns summary of what was consolidated.
    """
    window_days = _get_consolidation_window(db, factory_id)
    half_window = datetime.now(timezone.utc) - timedelta(days=window_days / 2)

    candidates = find_consolidation_candidates(db, factory_id)
    results = []

    for group in candidates:
        pr_ids = group["pr_ids"]
        pr_count = group["pr_count"]

        # Auto-consolidate if 3+ PRs, or 2+ PRs older than half window
        should_auto = pr_count >= 3
        if not should_auto and pr_count >= 2:
            earliest = group.get("earliest_created")
            if earliest:
                earliest_dt = datetime.fromisoformat(earliest)
                if earliest_dt.tzinfo is None:
                    earliest_dt = earliest_dt.replace(tzinfo=timezone.utc)
                should_auto = earliest_dt <= half_window

        if should_auto:
            try:
                pr_uuid_ids = [UUID(pid) for pid in pr_ids]
                # Use factory_id as consolidated_by for auto operations
                result = consolidate_purchase_requests(db, pr_uuid_ids, factory_id)
                results.append(result)
            except (ValueError, Exception) as e:
                logger.warning(f"Auto-consolidation failed for supplier {group['supplier_id']}: {e}")

    if results:
        db.commit()
        logger.info(f"Auto-consolidated {len(results)} groups for factory {str(factory_id)[:8]}")

    return {
        "factory_id": str(factory_id),
        "groups_consolidated": len(results),
        "details": results,
    }
