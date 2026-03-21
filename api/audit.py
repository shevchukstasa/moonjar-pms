"""
Audit logging utility — records all destructive operations.

Usage in routers:
    from api.audit import log_delete

    @router.delete("/{item_id}")
    def delete_item(item_id: UUID, db: Session = ..., current_user = ...):
        item = db.query(Model).get(item_id)
        log_delete(db, "table_name", item_id, item.__dict__, current_user)
        db.delete(item)
        db.commit()
"""
import logging
from uuid import UUID
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def log_delete(
    db: Session,
    table_name: str,
    record_id: UUID,
    old_data: dict | None = None,
    current_user=None,
    action: str = "DELETE",
):
    """Write an audit log entry for a destructive operation.

    Args:
        db: SQLAlchemy session
        table_name: Name of the affected table
        record_id: UUID of the deleted/deactivated record
        old_data: Snapshot of the record before deletion
        current_user: Current authenticated user (has .id, .email)
        action: Type of action (DELETE, DEACTIVATE, etc.)
    """
    from api.models import AuditLog

    # Clean old_data — remove SQLAlchemy internal fields
    clean_data = None
    if old_data:
        clean_data = {}
        for k, v in old_data.items():
            if k.startswith('_'):
                continue
            try:
                # Convert UUIDs, Decimals, dates to strings for JSON
                import json
                json.dumps(v)
                clean_data[k] = v
            except (TypeError, ValueError):
                clean_data[k] = str(v)

    try:
        entry = AuditLog(
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_data=clean_data,
            user_id=current_user.id if current_user else None,
            user_email=getattr(current_user, 'email', None),
        )
        db.add(entry)
        # Don't commit — let the caller manage the transaction
        logger.info(
            "AUDIT | %s %s.%s by %s",
            action, table_name, record_id,
            getattr(current_user, 'email', 'system'),
        )
    except Exception as e:
        logger.warning("Audit log write failed: %s", e)
