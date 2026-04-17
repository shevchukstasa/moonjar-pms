"""
Skill Badge System — learnable skills and certifications for factory workers.

Workers progress through skills by completing operations with low defect rates.
Skills auto-certify when requirements are met (unless mentor approval is needed).
Cross-training badges are computed from the total number of certified skills.

Categories:
- production (10): core tile manufacturing operations
- specialized (4): advanced techniques requiring precision
- quality (2): defect detection and QC inspection
- safety (1): equipment maintenance certification
- leadership (1): training and mentoring others
- cross_training (2): breadth of skills across stages
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func

from api.models import SkillBadge, UserSkill, OperationLog, User, Operation, UserFactory
from api.enums import UserRole
from business.services.points_system import award_points
from business.services.notifications import notify_pm, send_telegram_message

logger = logging.getLogger("moonjar.skill_system")

# ── Default skill definitions ─────────────────────────────────────

SKILL_DEFINITIONS: list[dict] = [
    # --- Production (10) ---
    {
        "code": "unpacking",
        "name": "Unpacking & Sorting Raw Materials",
        "name_id": "Pembongkaran & Penyortiran Bahan Baku",
        "category": "production",
        "icon": "\U0001F4E6",  # package
        "description": "Receive, inspect, and sort raw stone tiles by grade and size.",
        "required_operations": 30,
        "required_zero_defect_pct": Decimal("85"),
        "required_mentor_approval": False,
        "points_on_earn": 80,
    },
    {
        "code": "engobe_application",
        "name": "Engobe Application",
        "name_id": "Pengaplikasian Engobe",
        "category": "production",
        "icon": "\U0001F58C",  # paintbrush
        "description": "Apply engobe base coat evenly before glazing. Consistent thickness required.",
        "required_operations": 50,
        "required_zero_defect_pct": Decimal("90"),
        "required_mentor_approval": False,
        "points_on_earn": 100,
    },
    {
        "code": "glazing_spray",
        "name": "Spray Glazing",
        "name_id": "Pengglasiran Semprot",
        "category": "production",
        "icon": "\U0001F4A8",  # dash / spray
        "description": "Spray glaze application with even coverage. Master spray gun distance and pressure.",
        "required_operations": 60,
        "required_zero_defect_pct": Decimal("90"),
        "required_mentor_approval": False,
        "points_on_earn": 120,
    },
    {
        "code": "glazing_dip",
        "name": "Dip Glazing",
        "name_id": "Pengglasiran Celup",
        "category": "production",
        "icon": "\U0001F30A",  # wave
        "description": "Submerge tiles in glaze bath. Control immersion time and angle.",
        "required_operations": 50,
        "required_zero_defect_pct": Decimal("90"),
        "required_mentor_approval": False,
        "points_on_earn": 100,
    },
    {
        "code": "glazing_brush",
        "name": "Brush Glazing",
        "name_id": "Pengglasiran Kuas",
        "category": "production",
        "icon": "\U0001F58C",  # paintbrush
        "description": "Hand-brush glaze for artistic effects and custom patterns.",
        "required_operations": 40,
        "required_zero_defect_pct": Decimal("88"),
        "required_mentor_approval": False,
        "points_on_earn": 100,
    },
    {
        "code": "edge_cleaning",
        "name": "Edge Cleaning",
        "name_id": "Pembersihan Tepi",
        "category": "production",
        "icon": "\U00002702",  # scissors
        "description": "Remove excess glaze from tile edges before firing. Prevents sticking.",
        "required_operations": 40,
        "required_zero_defect_pct": Decimal("92"),
        "required_mentor_approval": False,
        "points_on_earn": 80,
    },
    {
        "code": "kiln_loading",
        "name": "Kiln Loading",
        "name_id": "Pemuatan Kiln",
        "category": "production",
        "icon": "\U0001F9F1",  # brick
        "description": "Load tiles onto kiln shelves with proper spacing and zone placement.",
        "required_operations": 40,
        "required_zero_defect_pct": Decimal("88"),
        "required_mentor_approval": False,
        "points_on_earn": 100,
    },
    {
        "code": "firing_management",
        "name": "Firing Management",
        "name_id": "Manajemen Pembakaran",
        "category": "production",
        "icon": "\U0001F525",  # fire
        "description": "Monitor kiln temperature curves and manage firing profiles.",
        "required_operations": 30,
        "required_zero_defect_pct": Decimal("92"),
        "required_mentor_approval": True,
        "points_on_earn": 150,
    },
    {
        "code": "sorting",
        "name": "Sorting & Grading",
        "name_id": "Penyortiran & Penilaian",
        "category": "production",
        "icon": "\U0001F50D",  # magnifying glass
        "description": "Sort fired tiles by quality grade. Identify and classify defects.",
        "required_operations": 60,
        "required_zero_defect_pct": Decimal("90"),
        "required_mentor_approval": False,
        "points_on_earn": 100,
    },
    {
        "code": "packing",
        "name": "Packing & Labeling",
        "name_id": "Pengemasan & Pelabelan",
        "category": "production",
        "icon": "\U0001F4E6",  # package
        "description": "Pack tiles safely with proper labeling for shipment.",
        "required_operations": 40,
        "required_zero_defect_pct": Decimal("85"),
        "required_mentor_approval": False,
        "points_on_earn": 80,
    },
    # --- Specialized (4) ---
    {
        "code": "recipe_mixing",
        "name": "Recipe Mixing",
        "name_id": "Pencampuran Resep",
        "category": "specialized",
        "icon": "\U00002697",  # alembic
        "description": "Mix glaze and engobe recipes to exact specifications. Precision weighing required.",
        "required_operations": 40,
        "required_zero_defect_pct": Decimal("95"),
        "required_mentor_approval": True,
        "points_on_earn": 200,
    },
    {
        "code": "color_matching",
        "name": "Color Matching",
        "name_id": "Pencocokan Warna",
        "category": "specialized",
        "icon": "\U0001F3A8",  # palette
        "description": "Match glaze colors to reference samples. Requires trained eye.",
        "required_operations": 30,
        "required_zero_defect_pct": Decimal("93"),
        "required_mentor_approval": True,
        "points_on_earn": 200,
    },
    {
        "code": "stencil_application",
        "name": "Stencil Application",
        "name_id": "Pengaplikasian Stensil",
        "category": "specialized",
        "icon": "\U0001F4D0",  # triangular ruler
        "description": "Apply stencil patterns with precision alignment and clean edges.",
        "required_operations": 40,
        "required_zero_defect_pct": Decimal("90"),
        "required_mentor_approval": True,
        "points_on_earn": 180,
    },
    {
        "code": "kiln_temp_mgmt",
        "name": "Kiln Temperature Management",
        "name_id": "Manajemen Suhu Kiln",
        "category": "specialized",
        "icon": "\U0001F321",  # thermometer
        "description": "Advanced temperature curve control. Handle multi-round firings and raku profiles.",
        "required_operations": 30,
        "required_zero_defect_pct": Decimal("95"),
        "required_mentor_approval": True,
        "points_on_earn": 250,
    },
    # --- Quality (2) ---
    {
        "code": "defect_identification",
        "name": "Defect Identification",
        "name_id": "Identifikasi Cacat",
        "category": "quality",
        "icon": "\U0001F9D0",  # monocle face
        "description": "Identify and classify all defect types: cracks, crawling, pinholes, color deviation.",
        "required_operations": 50,
        "required_zero_defect_pct": Decimal("90"),
        "required_mentor_approval": True,
        "points_on_earn": 150,
    },
    {
        "code": "qc_inspection",
        "name": "QC Inspection",
        "name_id": "Inspeksi Kontrol Kualitas",
        "category": "quality",
        "icon": "\U00002705",  # check mark
        "description": "Perform final quality control inspection per checklist. Sign off on batches.",
        "required_operations": 40,
        "required_zero_defect_pct": Decimal("93"),
        "required_mentor_approval": True,
        "points_on_earn": 180,
    },
    # --- Safety (1) ---
    {
        "code": "equipment_maintenance",
        "name": "Equipment Maintenance",
        "name_id": "Pemeliharaan Peralatan",
        "category": "safety",
        "icon": "\U0001F527",  # wrench
        "description": "Basic maintenance of spray guns, kilns, and glazing equipment. Safety protocols.",
        "required_operations": 20,
        "required_zero_defect_pct": Decimal("85"),
        "required_mentor_approval": True,
        "points_on_earn": 150,
    },
    # --- Leadership (1) ---
    {
        "code": "team_training",
        "name": "Team Training",
        "name_id": "Pelatihan Tim",
        "category": "leadership",
        "icon": "\U0001F393",  # graduation cap
        "description": "Train and mentor junior workers. Requires 5+ certified production skills.",
        "required_operations": 20,
        "required_zero_defect_pct": Decimal("85"),
        "required_mentor_approval": True,
        "points_on_earn": 300,
    },
    # --- Cross-training (2) ---
    {
        "code": "cross_stage_2",
        "name": "Cross-Training: 2 Stages",
        "name_id": "Lintas Pelatihan: 2 Tahap",
        "category": "cross_training",
        "icon": "\U0001F504",  # arrows counterclockwise
        "description": "Certified in at least 2 different production skills. Auto-awarded.",
        "required_operations": 0,
        "required_zero_defect_pct": Decimal("0"),
        "required_mentor_approval": False,
        "points_on_earn": 100,
    },
    {
        "code": "cross_stage_4",
        "name": "Cross-Training: 4 Stages",
        "name_id": "Lintas Pelatihan: 4 Tahap",
        "category": "cross_training",
        "icon": "\U0001F31F",  # glowing star
        "description": "Certified in at least 4 different production skills. Auto-awarded.",
        "required_operations": 0,
        "required_zero_defect_pct": Decimal("0"),
        "required_mentor_approval": False,
        "points_on_earn": 250,
    },
]

# Cross-training thresholds: code -> required certified production skills count
_CROSS_TRAINING_THRESHOLDS = {
    "cross_stage_2": 2,
    "cross_stage_4": 4,
}

# How many recent operations to use for defect-free percentage calculation
_DEFECT_WINDOW = 50


# ── Seed factory skills ──────────────────────────────────────────

def seed_factory_skills(db: Session, factory_id: UUID) -> list[SkillBadge]:
    """Create default skill badges for a factory. Skips already-existing codes."""
    existing_codes = set(
        row[0] for row in
        db.query(SkillBadge.code)
        .filter(SkillBadge.factory_id == factory_id)
        .all()
    )

    created = []
    for defn in SKILL_DEFINITIONS:
        if defn["code"] in existing_codes:
            continue

        badge = SkillBadge(
            factory_id=factory_id,
            code=defn["code"],
            name=defn["name"],
            name_id=defn["name_id"],
            category=defn["category"],
            icon=defn["icon"],
            description=defn["description"],
            required_operations=defn["required_operations"],
            required_zero_defect_pct=defn["required_zero_defect_pct"],
            required_mentor_approval=defn["required_mentor_approval"],
            points_on_earn=defn["points_on_earn"],
        )
        db.add(badge)
        created.append(badge)

    if created:
        db.flush()
        logger.info(
            "Seeded %d skill badges for factory %s (skipped %d existing)",
            len(created), factory_id, len(existing_codes),
        )
    return created


# ── Read queries ─────────────────────────────────────────────────

def get_factory_skills(db: Session, factory_id: UUID) -> list[dict]:
    """All available skills for a factory with certified user count per skill."""
    badges = (
        db.query(SkillBadge)
        .filter(
            SkillBadge.factory_id == factory_id,
            SkillBadge.is_active.is_(True),
        )
        .order_by(SkillBadge.category, SkillBadge.code)
        .all()
    )

    badge_ids = [b.id for b in badges]

    # Count certified users per badge in one query
    certified_counts = dict(
        db.query(UserSkill.skill_badge_id, sa_func.count(UserSkill.id))
        .filter(
            UserSkill.skill_badge_id.in_(badge_ids),
            UserSkill.status == "certified",
        )
        .group_by(UserSkill.skill_badge_id)
        .all()
    ) if badge_ids else {}

    # Count learners per badge
    learning_counts = dict(
        db.query(UserSkill.skill_badge_id, sa_func.count(UserSkill.id))
        .filter(
            UserSkill.skill_badge_id.in_(badge_ids),
            UserSkill.status.in_(["learning", "pending_approval"]),
        )
        .group_by(UserSkill.skill_badge_id)
        .all()
    ) if badge_ids else {}

    return [
        {
            "id": str(b.id),
            "code": b.code,
            "name": b.name,
            "name_id": b.name_id,
            "category": b.category,
            "icon": b.icon,
            "description": b.description,
            "required_operations": b.required_operations,
            "required_zero_defect_pct": float(b.required_zero_defect_pct or 0),
            "required_mentor_approval": b.required_mentor_approval,
            "points_on_earn": b.points_on_earn,
            "certified_count": certified_counts.get(b.id, 0),
            "learning_count": learning_counts.get(b.id, 0),
        }
        for b in badges
    ]


def get_user_skills(db: Session, user_id: UUID) -> list[dict]:
    """User's skill progress: certified, in-progress, and available badges."""
    # Get user's factory
    uf = db.query(UserFactory).filter(UserFactory.user_id == user_id).first()
    if not uf:
        logger.warning("get_user_skills: user %s has no factory assignment", user_id)
        return []

    # All active badges for this factory
    badges = (
        db.query(SkillBadge)
        .filter(
            SkillBadge.factory_id == uf.factory_id,
            SkillBadge.is_active.is_(True),
        )
        .order_by(SkillBadge.category, SkillBadge.code)
        .all()
    )

    # User's skill records
    user_skills = {
        us.skill_badge_id: us
        for us in db.query(UserSkill)
        .filter(UserSkill.user_id == user_id)
        .all()
    }

    result = []
    for badge in badges:
        us = user_skills.get(badge.id)
        progress_pct = 0.0
        if us and badge.required_operations > 0:
            progress_pct = min(
                100.0,
                (us.operations_completed / badge.required_operations) * 100,
            )

        result.append({
            "badge_id": str(badge.id),
            "code": badge.code,
            "name": badge.name,
            "name_id": badge.name_id,
            "category": badge.category,
            "icon": badge.icon,
            "required_operations": badge.required_operations,
            "required_zero_defect_pct": float(badge.required_zero_defect_pct or 0),
            "required_mentor_approval": badge.required_mentor_approval,
            "points_on_earn": badge.points_on_earn,
            # Progress
            "status": us.status if us else "available",
            "operations_completed": us.operations_completed if us else 0,
            "defect_free_pct": float(us.defect_free_pct) if us else 0.0,
            "progress_pct": round(progress_pct, 1),
            "certified_at": us.certified_at.isoformat() if us and us.certified_at else None,
            "started_at": us.started_at.isoformat() if us else None,
            "user_skill_id": str(us.id) if us else None,
        })

    return result


# ── Learning lifecycle ───────────────────────────────────────────

def start_skill_learning(
    db: Session,
    user_id: UUID,
    skill_badge_id: UUID,
) -> UserSkill:
    """Begin tracking a skill for a worker. Idempotent: returns existing if found."""
    existing = (
        db.query(UserSkill)
        .filter(
            UserSkill.user_id == user_id,
            UserSkill.skill_badge_id == skill_badge_id,
        )
        .first()
    )
    if existing:
        logger.info(
            "Skill learning already started: user=%s badge=%s status=%s",
            user_id, skill_badge_id, existing.status,
        )
        return existing

    # Verify badge exists and is active
    badge = db.query(SkillBadge).filter(
        SkillBadge.id == skill_badge_id,
        SkillBadge.is_active.is_(True),
    ).first()
    if not badge:
        raise ValueError(f"Skill badge {skill_badge_id} not found or inactive")

    us = UserSkill(
        user_id=user_id,
        skill_badge_id=skill_badge_id,
        status="learning",
        operations_completed=0,
        defect_free_pct=Decimal("0"),
    )
    db.add(us)
    db.flush()

    logger.info(
        "Started skill learning: user=%s badge=%s (%s)",
        user_id, badge.code, badge.name,
    )
    return us


def update_skill_progress(
    db: Session,
    user_id: UUID,
    operation_id: UUID,
    quantity: int = 1,
    defects: int = 0,
) -> list[dict]:
    """
    Called after OperationLog is created. Updates all matching skills.

    Returns list of status changes (for notification purposes):
        [{"badge_code": ..., "old_status": ..., "new_status": ..., "badge": ...}]
    """
    # Find all learning/pending skills that match this operation via badge.operation_id
    user_skills = (
        db.query(UserSkill)
        .join(SkillBadge, UserSkill.skill_badge_id == SkillBadge.id)
        .filter(
            UserSkill.user_id == user_id,
            UserSkill.status.in_(["learning", "pending_approval"]),
            SkillBadge.operation_id == operation_id,
            SkillBadge.is_active.is_(True),
        )
        .options(joinedload(UserSkill.skill_badge))
        .all()
    )

    if not user_skills:
        return []

    changes = []

    for us in user_skills:
        badge = us.skill_badge
        old_status = us.status

        # Increment operations count
        us.operations_completed = (us.operations_completed or 0) + quantity

        # Recalculate defect-free percentage from recent operations
        us.defect_free_pct = _calc_defect_free_pct(db, user_id, operation_id)

        # Check if requirements are met
        ops_met = us.operations_completed >= badge.required_operations
        quality_met = us.defect_free_pct >= (badge.required_zero_defect_pct or 0)

        if ops_met and quality_met:
            if badge.required_mentor_approval:
                if us.status != "pending_approval":
                    us.status = "pending_approval"
                    logger.info(
                        "Skill ready for approval: user=%s badge=%s (%s)",
                        user_id, badge.code, badge.name,
                    )
                    _notify_pending_approval(db, user_id, badge)
            else:
                # Auto-certify
                us.status = "certified"
                us.certified_at = datetime.now(timezone.utc)
                logger.info(
                    "Auto-certified skill: user=%s badge=%s (%s)",
                    user_id, badge.code, badge.name,
                )
                _award_skill_points(db, user_id, badge)

        if us.status != old_status:
            changes.append({
                "badge_code": badge.code,
                "old_status": old_status,
                "new_status": us.status,
                "badge": badge,
            })

    db.flush()
    return changes


def _calc_defect_free_pct(
    db: Session,
    user_id: UUID,
    operation_id: UUID,
) -> Decimal:
    """Calculate defect-free percentage from the last N operations."""
    recent = (
        db.query(
            sa_func.coalesce(sa_func.sum(OperationLog.quantity_processed), 0).label("total"),
            sa_func.coalesce(sa_func.sum(OperationLog.defect_count), 0).label("defects"),
        )
        .filter(
            OperationLog.user_id == user_id,
            OperationLog.operation_id == operation_id,
        )
        .order_by(OperationLog.shift_date.desc())
        .limit(_DEFECT_WINDOW)
        .subquery()
    )

    # The subquery limits rows but we need the aggregation of those rows
    row = (
        db.query(
            sa_func.coalesce(sa_func.sum(recent.c.total), 0),
            sa_func.coalesce(sa_func.sum(recent.c.defects), 0),
        )
        .first()
    )

    total_qty = int(row[0])
    total_defects = int(row[1])

    if total_qty == 0:
        return Decimal("0")

    defect_free = ((total_qty - total_defects) / total_qty) * 100
    return Decimal(str(round(defect_free, 2)))


# ── Batch nightly recalculation ──────────────────────────────────

def batch_update_all_skills(db: Session) -> dict:
    """
    Nightly cron job: recalculate progress for all active learners.
    Also checks and awards cross-training badges.

    Returns summary: {"updated": int, "auto_certified": int, "cross_awarded": int}
    """
    summary = {"updated": 0, "auto_certified": 0, "cross_awarded": 0}

    # 1. Recalculate all 'learning' skills from OperationLog
    learning_skills = (
        db.query(UserSkill)
        .join(SkillBadge, UserSkill.skill_badge_id == SkillBadge.id)
        .filter(
            UserSkill.status == "learning",
            SkillBadge.is_active.is_(True),
            SkillBadge.category != "cross_training",  # handled separately
            SkillBadge.operation_id.isnot(None),
        )
        .options(joinedload(UserSkill.skill_badge))
        .all()
    )

    for us in learning_skills:
        badge = us.skill_badge

        # Count total operations from log
        total_ops = (
            db.query(sa_func.coalesce(sa_func.count(OperationLog.id), 0))
            .filter(
                OperationLog.user_id == us.user_id,
                OperationLog.operation_id == badge.operation_id,
            )
            .scalar()
        )
        us.operations_completed = total_ops

        # Recalculate defect pct
        us.defect_free_pct = _calc_defect_free_pct(
            db, us.user_id, badge.operation_id,
        )

        # Check requirements
        ops_met = us.operations_completed >= badge.required_operations
        quality_met = us.defect_free_pct >= (badge.required_zero_defect_pct or 0)

        if ops_met and quality_met:
            if badge.required_mentor_approval:
                if us.status != "pending_approval":
                    us.status = "pending_approval"
                    _notify_pending_approval(db, us.user_id, badge)
            else:
                us.status = "certified"
                us.certified_at = datetime.now(timezone.utc)
                _award_skill_points(db, us.user_id, badge)
                summary["auto_certified"] += 1

        summary["updated"] += 1

    # 2. Cross-training badges
    summary["cross_awarded"] += _check_cross_training_badges(db)

    db.flush()
    logger.info(
        "Batch skill update complete: %d updated, %d auto-certified, %d cross-training awarded",
        summary["updated"], summary["auto_certified"], summary["cross_awarded"],
    )
    return summary


def _check_cross_training_badges(db: Session) -> int:
    """Award cross-training badges based on certified production skill count."""
    awarded = 0

    # Get all users who have at least 1 certified production skill
    users_with_skills = (
        db.query(
            UserSkill.user_id,
            sa_func.count(UserSkill.id).label("cert_count"),
        )
        .join(SkillBadge, UserSkill.skill_badge_id == SkillBadge.id)
        .filter(
            UserSkill.status == "certified",
            SkillBadge.category == "production",
            SkillBadge.is_active.is_(True),
        )
        .group_by(UserSkill.user_id)
        .all()
    )

    for user_id, cert_count in users_with_skills:
        for cross_code, threshold in _CROSS_TRAINING_THRESHOLDS.items():
            if cert_count < threshold:
                continue

            # Find the cross-training badge for this user's factory
            uf = db.query(UserFactory).filter(UserFactory.user_id == user_id).first()
            if not uf:
                continue

            badge = (
                db.query(SkillBadge)
                .filter(
                    SkillBadge.factory_id == uf.factory_id,
                    SkillBadge.code == cross_code,
                    SkillBadge.is_active.is_(True),
                )
                .first()
            )
            if not badge:
                continue

            # Check if already earned or in progress
            existing = (
                db.query(UserSkill)
                .filter(
                    UserSkill.user_id == user_id,
                    UserSkill.skill_badge_id == badge.id,
                )
                .first()
            )
            if existing and existing.status == "certified":
                continue

            if existing:
                existing.status = "certified"
                existing.certified_at = datetime.now(timezone.utc)
                existing.operations_completed = cert_count
            else:
                us = UserSkill(
                    user_id=user_id,
                    skill_badge_id=badge.id,
                    status="certified",
                    operations_completed=cert_count,
                    defect_free_pct=Decimal("100"),
                    certified_at=datetime.now(timezone.utc),
                )
                db.add(us)

            _award_skill_points(db, user_id, badge)
            awarded += 1

            logger.info(
                "Cross-training badge awarded: user=%s code=%s (has %d production skills)",
                user_id, cross_code, cert_count,
            )

    return awarded


# ── Certification workflow ───────────────────────────────────────

def request_certification(
    db: Session,
    user_id: UUID,
    skill_badge_id: UUID,
) -> UserSkill:
    """Worker requests PM approval for a skill certification."""
    us = (
        db.query(UserSkill)
        .filter(
            UserSkill.user_id == user_id,
            UserSkill.skill_badge_id == skill_badge_id,
        )
        .options(joinedload(UserSkill.skill_badge))
        .first()
    )
    if not us:
        raise ValueError("No skill record found. Start learning first.")

    if us.status == "certified":
        raise ValueError("Skill is already certified.")

    if us.status == "pending_approval":
        logger.info("Certification already pending: user=%s badge=%s", user_id, skill_badge_id)
        return us

    badge = us.skill_badge

    # Validate minimum requirements before allowing request
    ops_met = us.operations_completed >= badge.required_operations
    quality_met = us.defect_free_pct >= (badge.required_zero_defect_pct or 0)

    if not ops_met:
        raise ValueError(
            f"Need {badge.required_operations} operations, have {us.operations_completed}."
        )
    if not quality_met:
        raise ValueError(
            f"Need {badge.required_zero_defect_pct}% defect-free, currently at {us.defect_free_pct}%."
        )

    us.status = "pending_approval"
    db.flush()

    _notify_pending_approval(db, user_id, badge)

    logger.info(
        "Certification requested: user=%s badge=%s (%s)",
        user_id, badge.code, badge.name,
    )
    return us


def approve_certification(
    db: Session,
    approver_id: UUID,
    user_skill_id: UUID,
) -> UserSkill:
    """PM approves a worker's skill certification. Awards points and notifies."""
    us = (
        db.query(UserSkill)
        .filter(UserSkill.id == user_skill_id)
        .options(joinedload(UserSkill.skill_badge), joinedload(UserSkill.user))
        .first()
    )
    if not us:
        raise ValueError(f"UserSkill {user_skill_id} not found")

    if us.status != "pending_approval":
        raise ValueError(
            f"Cannot approve skill in status '{us.status}'. Expected 'pending_approval'."
        )

    # Verify approver has PM/admin/owner role
    approver = db.query(User).filter(User.id == approver_id).first()
    if not approver:
        raise ValueError("Approver not found")

    allowed_roles = {UserRole.production_manager, UserRole.administrator, UserRole.owner, UserRole.ceo}
    if approver.role not in allowed_roles:
        raise ValueError(f"User with role '{approver.role}' cannot approve certifications")

    us.status = "certified"
    us.certified_at = datetime.now(timezone.utc)
    us.certified_by = approver_id
    db.flush()

    badge = us.skill_badge
    worker = us.user

    # Award points
    _award_skill_points(db, us.user_id, badge)

    # Notify worker via Telegram
    worker_name = f"{worker.first_name or ''} {worker.last_name or ''}".strip() or "Worker"
    _send_certification_notification(db, worker, badge, worker_name)

    logger.info(
        "Certification approved: user=%s badge=%s (%s) by approver=%s",
        us.user_id, badge.code, badge.name, approver_id,
    )
    return us


def revoke_certification(
    db: Session,
    revoker_id: UUID,
    user_skill_id: UUID,
    reason: str,
) -> UserSkill:
    """PM revokes a certification (quality dropped, safety concern, etc.)."""
    if not reason or not reason.strip():
        raise ValueError("Revocation reason is required")

    us = (
        db.query(UserSkill)
        .filter(UserSkill.id == user_skill_id)
        .options(joinedload(UserSkill.skill_badge), joinedload(UserSkill.user))
        .first()
    )
    if not us:
        raise ValueError(f"UserSkill {user_skill_id} not found")

    if us.status != "certified":
        raise ValueError(
            f"Cannot revoke skill in status '{us.status}'. Expected 'certified'."
        )

    # Verify revoker permissions
    revoker = db.query(User).filter(User.id == revoker_id).first()
    if not revoker:
        raise ValueError("Revoker not found")

    allowed_roles = {UserRole.production_manager, UserRole.administrator, UserRole.owner, UserRole.ceo}
    if revoker.role not in allowed_roles:
        raise ValueError(f"User with role '{revoker.role}' cannot revoke certifications")

    old_status = us.status
    us.status = "revoked"
    us.certified_at = None
    us.certified_by = None
    db.flush()

    badge = us.skill_badge
    worker = us.user
    worker_name = f"{worker.first_name or ''} {worker.last_name or ''}".strip() or "Worker"

    logger.warning(
        "Certification revoked: user=%s (%s) badge=%s (%s) reason='%s' by revoker=%s",
        us.user_id, worker_name, badge.code, badge.name, reason, revoker_id,
    )

    # Notify PM channel about revocation
    try:
        uf = db.query(UserFactory).filter(UserFactory.user_id == us.user_id).first()
        if uf:
            notify_pm(
                db,
                uf.factory_id,
                type="skill_revoked",
                title=f"Skill revoked: {worker_name} — {badge.name}",
                message=f"Reason: {reason}",
            )
    except Exception:
        logger.exception("Failed to send revocation notification")

    return us


# ── Internal helpers ─────────────────────────────────────────────

def _award_skill_points(db: Session, user_id: UUID, badge: SkillBadge) -> None:
    """Award points for earning a skill badge."""
    try:
        uf = db.query(UserFactory).filter(UserFactory.user_id == user_id).first()
        if not uf:
            logger.warning("Cannot award skill points: user %s has no factory", user_id)
            return

        award_points(
            db=db,
            user_id=user_id,
            factory_id=uf.factory_id,
            points=badge.points_on_earn,
            reason="skill_certification",
            details={
                "badge_code": badge.code,
                "badge_name": badge.name,
                "category": badge.category,
            },
        )
        logger.info(
            "Awarded %d points for skill %s to user %s",
            badge.points_on_earn, badge.code, user_id,
        )
    except Exception:
        logger.exception("Failed to award skill points: user=%s badge=%s", user_id, badge.code)


def _notify_pending_approval(db: Session, user_id: UUID, badge: SkillBadge) -> None:
    """Notify PM that a worker's skill is ready for approval."""
    try:
        worker = db.query(User).filter(User.id == user_id).first()
        worker_name = "Worker"
        if worker:
            worker_name = f"{worker.first_name or ''} {worker.last_name or ''}".strip() or "Worker"

        uf = db.query(UserFactory).filter(UserFactory.user_id == user_id).first()
        if uf:
            notify_pm(
                db,
                uf.factory_id,
                type="skill_pending_approval",
                title=f"Запрос сертификации: {worker_name}",
                message=(
                    f"{badge.icon} {badge.name} ({badge.name_id})\n"
                    f"Категория: {badge.category}\n"
                    f"Работник выполнил все требования и ждёт вашего одобрения."
                ),
            )
    except Exception:
        logger.exception("Failed to send pending approval notification")


def _send_certification_notification(
    db: Session,
    worker: User,
    badge: SkillBadge,
    worker_name: str,
) -> None:
    """Send Telegram congratulation to the worker."""
    try:
        if not worker.telegram_chat_id:
            return

        text = (
            f"Поздравляем, {worker_name}! {badge.icon}\n\n"
            f"Вы получили сертификацию:\n"
            f"*{badge.name}*\n"
            f"_{badge.name_id}_\n\n"
            f"Начислено очков: +{badge.points_on_earn}\n"
            f"Продолжайте совершенствовать мастерство!"
        )
        send_telegram_message(worker.telegram_chat_id, text)
    except Exception:
        logger.exception("Failed to send certification Telegram notification to user %s", worker.id)
