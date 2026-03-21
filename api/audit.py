"""
Moonjar PMS — Automatic Audit Logger.

Uses SQLAlchemy session events to capture ALL database mutations (INSERT, UPDATE, DELETE)
without requiring manual AuditLog calls in every router.

User context (user_id, user_email, request_path) is passed via contextvars,
set by AuditContextMiddleware in api/middleware.py.

The legacy log_delete() function is preserved for backward compatibility with
existing routers that call it directly.
"""

import json
import logging
import uuid as _uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import event, inspect, text
from sqlalchemy.orm import Session

logger = logging.getLogger("moonjar.audit")

# ---------------------------------------------------------------------------
# Context variables (set by middleware, read by audit listener)
# ---------------------------------------------------------------------------

audit_user_id: ContextVar[Optional[str]] = ContextVar("audit_user_id", default=None)
audit_user_email: ContextVar[Optional[str]] = ContextVar("audit_user_email", default=None)
audit_request_path: ContextVar[Optional[str]] = ContextVar("audit_request_path", default=None)
audit_ip_address: ContextVar[Optional[str]] = ContextVar("audit_ip_address", default=None)

# Tables that should NOT be audited (internal / meta / high-churn)
SKIP_TABLES = frozenset({
    "audit_logs",
    "alembic_version",
    "rag_embeddings",
    "rate_limit_events",
    "security_audit_log",
    "active_sessions",
    "backup_logs",
})

# Maximum size for JSONB payloads to avoid bloating audit_logs
_MAX_JSONB_CHARS = 50_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_value(val):
    """Convert a value to JSON-serializable form."""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, _uuid.UUID):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, (list, dict)):
        return val
    # Enum values
    if hasattr(val, "value"):
        return val.value
    try:
        return str(val)
    except Exception:
        return "<unserializable>"


def _get_record_id(obj) -> Optional[str]:
    """Extract primary key value from an ORM object."""
    mapper = inspect(type(obj))
    pk_cols = mapper.primary_key
    if not pk_cols:
        return None
    pk_val = getattr(obj, pk_cols[0].name, None)
    if pk_val is None:
        return None
    return str(pk_val)


def _get_object_data(obj) -> dict:
    """Serialize all column values of an ORM object to a dict."""
    mapper = inspect(type(obj))
    data = {}
    for col in mapper.columns:
        try:
            val = getattr(obj, col.key, None)
            data[col.key] = _serialize_value(val)
        except Exception:
            data[col.key] = "<error>"
    # Truncate if too large
    serialized = json.dumps(data, default=str)
    if len(serialized) > _MAX_JSONB_CHARS:
        keys = list(data.keys())[:20]
        data = {k: data[k] for k in keys}
        data["_truncated"] = True
    return data


def _get_changed_data(obj) -> tuple[dict, dict]:
    """For a dirty (updated) object, return (old_data, new_data) with only changed columns."""
    insp = inspect(obj)
    old_data = {}
    new_data = {}
    for attr in insp.attrs:
        hist = attr.history
        if hist.has_changes():
            key = attr.key
            if hist.deleted:
                old_data[key] = _serialize_value(hist.deleted[0])
            if hist.added:
                new_data[key] = _serialize_value(hist.added[0])
    return old_data, new_data


def _build_audit_record(action: str, table_name: str, record_id: str,
                        old_data: Optional[dict], new_data: Optional[dict]) -> dict:
    """Build a raw audit log dict ready for bulk insert."""
    return {
        "id": str(_uuid.uuid4()),
        "action": action,
        "table_name": table_name,
        "record_id": record_id,
        "old_data": old_data,
        "new_data": new_data,
        "user_id": audit_user_id.get(),
        "user_email": audit_user_email.get(),
        "ip_address": audit_ip_address.get(),
        "request_path": audit_request_path.get(),
        "created_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# SQLAlchemy event listeners
# ---------------------------------------------------------------------------

def _audit_after_flush(session: Session, flush_context):
    """Capture all INSERTs, UPDATEs, DELETEs during flush."""
    audit_records = []

    try:
        # --- INSERTS ---
        for obj in session.new:
            table_name = getattr(obj, "__tablename__", None)
            if not table_name or table_name in SKIP_TABLES:
                continue
            record_id = _get_record_id(obj)
            if not record_id:
                continue
            new_data = _get_object_data(obj)
            audit_records.append(
                _build_audit_record("INSERT", table_name, record_id, None, new_data)
            )

        # --- UPDATES ---
        for obj in session.dirty:
            if not session.is_modified(obj, include_collections=False):
                continue
            table_name = getattr(obj, "__tablename__", None)
            if not table_name or table_name in SKIP_TABLES:
                continue
            record_id = _get_record_id(obj)
            if not record_id:
                continue
            old_data, new_data = _get_changed_data(obj)
            if not old_data and not new_data:
                continue
            audit_records.append(
                _build_audit_record("UPDATE", table_name, record_id, old_data, new_data)
            )

        # --- DELETES ---
        for obj in session.deleted:
            table_name = getattr(obj, "__tablename__", None)
            if not table_name or table_name in SKIP_TABLES:
                continue
            record_id = _get_record_id(obj)
            if not record_id:
                continue
            old_data = _get_object_data(obj)
            audit_records.append(
                _build_audit_record("DELETE", table_name, record_id, old_data, None)
            )

    except Exception as e:
        logger.error("Audit: error collecting changes: %s", e, exc_info=True)
        return

    if not audit_records:
        return

    # Queue records on the session for after_commit
    if not hasattr(session, "_pending_audit_records"):
        session._pending_audit_records = []
    session._pending_audit_records.extend(audit_records)


def _audit_after_commit(session: Session):
    """Write queued audit records AFTER the main transaction commits successfully.

    Uses a separate connection to avoid interfering with the main session.
    """
    records = getattr(session, "_pending_audit_records", None)
    if not records:
        return
    session._pending_audit_records = []

    try:
        from api.database import engine

        insert_sql = text("""
            INSERT INTO audit_logs
                (id, action, table_name, record_id, old_data, new_data,
                 user_id, user_email, ip_address, request_path, created_at)
            VALUES
                (:id, :action, :table_name, :record_id,
                 CAST(:old_data AS JSONB), CAST(:new_data AS JSONB),
                 CAST(:user_id AS UUID), :user_email, :ip_address, :request_path, :created_at)
        """)

        with engine.connect() as conn:
            for rec in records:
                try:
                    conn.execute(insert_sql, {
                        "id": rec["id"],
                        "action": rec["action"],
                        "table_name": rec["table_name"],
                        "record_id": rec["record_id"],
                        "old_data": json.dumps(rec["old_data"], default=str) if rec["old_data"] else None,
                        "new_data": json.dumps(rec["new_data"], default=str) if rec["new_data"] else None,
                        "user_id": rec["user_id"],
                        "user_email": rec["user_email"],
                        "ip_address": rec["ip_address"],
                        "request_path": rec["request_path"],
                        "created_at": rec["created_at"],
                    })
                except Exception as e:
                    logger.warning("Audit: failed to write %s on %s.%s: %s",
                                   rec["action"], rec["table_name"], rec["record_id"], e)
            conn.commit()

        logger.debug("Audit: wrote %d records", len(records))

    except Exception as e:
        # NEVER let audit logging crash the main application
        logger.error("Audit: bulk insert failed: %s", e, exc_info=True)


def _audit_after_rollback(session: Session):
    """Discard pending audit records on rollback — the changes didn't persist."""
    if hasattr(session, "_pending_audit_records"):
        session._pending_audit_records = []


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

_initialized = False


def init_audit_listeners():
    """Register SQLAlchemy event listeners for automatic audit logging.

    Call once at application startup.  Safe to call multiple times (idempotent).
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    event.listen(Session, "after_flush", _audit_after_flush)
    event.listen(Session, "after_commit", _audit_after_commit)
    event.listen(Session, "after_rollback", _audit_after_rollback)
    logger.info("Automatic audit logging initialized (after_flush + after_commit)")


# ---------------------------------------------------------------------------
# Legacy API — preserved for backward compatibility
# ---------------------------------------------------------------------------

def log_delete(
    db: Session,
    table_name: str,
    record_id,
    old_data: dict | None = None,
    current_user=None,
    action: str = "DELETE",
):
    """Write an audit log entry for a destructive operation.

    LEGACY: Kept for backward compatibility with existing routers that call
    it directly.  The automatic audit system now captures these operations
    via SQLAlchemy events, so new code does not need to call this.

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
        logger.info(
            "AUDIT | %s %s.%s by %s",
            action, table_name, record_id,
            getattr(current_user, 'email', 'system'),
        )
    except Exception as e:
        logger.warning("Audit log write failed: %s", e)
