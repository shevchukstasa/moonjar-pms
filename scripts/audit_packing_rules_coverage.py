"""Audit: every active Size in catalogue must have PackagingBoxCapacity.

Goal — implement BUSINESS_LOGIC_FULL §31 "Packing Rules":
  1. Walk all `Size` rows that are referenced by at least one
     non-terminal `OrderPosition`.
  2. For each, check if there is a `PackagingBoxCapacity` row.
  3. If missing — create a single PM-assigned `PACKING_MATERIALS_NEEDED`
     blocking task per Size (idempotent: one task per size, no
     duplicates if the script is re-run).

Usage:
    python -m scripts.audit_packing_rules_coverage
    python -m scripts.audit_packing_rules_coverage --factory <uuid>

Run-anywhere safe: read-only when --dry-run is set.
"""

import argparse
import logging
import sys
from uuid import UUID

# Project root on sys.path so this module can import api/* without `pip install`.
import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from sqlalchemy.orm import Session  # noqa: E402

logger = logging.getLogger("audit_packing_rules")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def audit_factory(db: Session, factory_id: UUID, dry_run: bool = False) -> dict:
    """Run the audit for one factory. Returns counts."""
    from api.models import (
        Size, OrderPosition, PackagingBoxCapacity, Task,
    )
    from api.enums import (
        PositionStatus, TaskType, TaskStatus, UserRole,
    )

    terminal = {
        PositionStatus.SHIPPED.value,
        PositionStatus.CANCELLED.value,
        PositionStatus.MERGED.value,
    }

    # Sizes referenced by at least one non-terminal position on this factory.
    size_ids = {
        row[0]
        for row in db.query(OrderPosition.size_id)
        .filter(
            OrderPosition.factory_id == factory_id,
            OrderPosition.size_id.isnot(None),
            ~OrderPosition.status.in_(list(terminal)),
        )
        .distinct()
        .all()
        if row[0] is not None
    }
    if not size_ids:
        logger.info("No active Sizes on factory %s — nothing to audit", factory_id)
        return {"sizes_checked": 0, "missing_rules": 0, "tasks_created": 0}

    logger.info(
        "Factory %s — %d distinct Sizes referenced by active positions",
        factory_id, len(size_ids),
    )

    sizes = db.query(Size).filter(Size.id.in_(list(size_ids))).all()

    missing: list[Size] = []
    for s in sizes:
        has_rule = (
            db.query(PackagingBoxCapacity)
            .filter(PackagingBoxCapacity.size_id == s.id)
            .first()
        )
        if not has_rule:
            missing.append(s)

    if not missing:
        logger.info("✓ Every active size has packaging rules — nothing to do")
        return {
            "sizes_checked": len(sizes),
            "missing_rules": 0,
            "tasks_created": 0,
        }

    logger.warning(
        "%d size(s) without PackagingBoxCapacity:\n  %s",
        len(missing),
        "\n  ".join(f"{s.id} — {s.name} ({s.shape or 'rectangle'})" for s in missing),
    )

    if dry_run:
        return {
            "sizes_checked": len(sizes),
            "missing_rules": len(missing),
            "tasks_created": 0,
            "dry_run": True,
        }

    # Idempotent task creation: skip if a pending PACKING_MATERIALS_NEEDED
    # task already exists with this size_id stamped in metadata_json.
    created = 0
    for s in missing:
        size_id_str = str(s.id)
        existing = (
            db.query(Task)
            .filter(
                Task.factory_id == factory_id,
                Task.type == TaskType.PACKING_MATERIALS_NEEDED.value,
                Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]),
            )
            .all()
        )
        already = any(
            (t.metadata_json or {}).get("size_id") == size_id_str
            for t in existing
        )
        if already:
            logger.info("  task already pending for size %s — skip", s.name)
            continue

        db.add(Task(
            factory_id=factory_id,
            type=TaskType.PACKING_MATERIALS_NEEDED.value,
            status=TaskStatus.PENDING.value,
            assigned_role=UserRole.PRODUCTION_MANAGER.value,
            blocking=False,  # not blocking the schedule, blocks /pack only
            description=(
                f"Заведи правила упаковки (PackagingBoxCapacity) для размера "
                f"«{s.name}» — без них pack-операция не пройдёт. "
                f"Shape: {s.shape or 'rectangle'}, "
                f"{s.width_mm}×{s.height_mm}"
                + (f"×{s.thickness_mm}" if s.thickness_mm else "")
                + " мм."
            ),
            metadata_json={
                "size_id": size_id_str,
                "size_name": s.name,
                "shape": s.shape or "rectangle",
                "width_mm": s.width_mm,
                "height_mm": s.height_mm,
                "thickness_mm": s.thickness_mm,
                "diameter_mm": s.diameter_mm,
                "source": "audit_packing_rules_coverage",
            },
        ))
        created += 1

    if created:
        db.commit()
        logger.info("Created %d new PM tasks", created)

    return {
        "sizes_checked": len(sizes),
        "missing_rules": len(missing),
        "tasks_created": created,
    }


def audit_all_factories(dry_run: bool = False) -> dict:
    from api.database import SessionLocal
    from api.models import Factory

    db = SessionLocal()
    try:
        factories = db.query(Factory).all()
        results = {}
        totals = {"sizes_checked": 0, "missing_rules": 0, "tasks_created": 0}
        for f in factories:
            r = audit_factory(db, f.id, dry_run=dry_run)
            results[str(f.id)] = {"name": f.name, **r}
            for k in totals:
                totals[k] += r.get(k, 0)
        return {"factories": results, "totals": totals}
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--factory", type=str, help="Only this factory_id (UUID)")
    p.add_argument("--dry-run", action="store_true", help="Don't create tasks, just report")
    args = p.parse_args()

    if args.factory:
        from api.database import SessionLocal
        db = SessionLocal()
        try:
            r = audit_factory(db, UUID(args.factory), dry_run=args.dry_run)
        finally:
            db.close()
        print(r)
    else:
        print(audit_all_factories(dry_run=args.dry_run))
