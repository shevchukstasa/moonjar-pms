"""Health check, backup monitoring & internal cron endpoints."""

import hmac
import os
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from api.database import get_db
from api.config import get_settings
from api.roles import require_admin

logger = logging.getLogger("moonjar.health")
router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "moonjar-pms"}


@router.get("/health/env-check")
async def env_check():
    """Public diagnostic: which integration keys are configured (values hidden)."""
    def _is_set(key: str) -> bool:
        val = os.getenv(key, "")
        return bool(val and len(val) > 3)

    return {
        "OPENAI_API_KEY": _is_set("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": _is_set("ANTHROPIC_API_KEY"),
        "TELEGRAM_BOT_TOKEN": _is_set("TELEGRAM_BOT_TOKEN"),
        "SUPABASE_URL": _is_set("SUPABASE_URL"),
        "SUPABASE_KEY": _is_set("SUPABASE_KEY"),
        "INTERNAL_API_KEY": _is_set("INTERNAL_API_KEY"),
        "GOOGLE_OAUTH_CLIENT_ID": _is_set("GOOGLE_OAUTH_CLIENT_ID"),
        "S3_BACKUP_BUCKET": _is_set("S3_BACKUP_BUCKET"),
    }


@router.get("/health/seed-status")
async def seed_status(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Admin-only diagnostic: count rows in key reference tables."""
    from sqlalchemy import text
    counts = {}
    for table in ["colors", "sizes", "firing_profiles", "factories", "users",
                   "recipes", "materials", "resources", "tps_parameters",
                   "application_methods", "application_collections", "color_collections",
                   "recipe_materials", "material_stock", "glazing_board_specs",
                   "defect_causes", "collections", "finishing_types", "application_types",
                   "places_of_application", "suppliers", "packaging_box_types",
                   "quality_assignment_config", "kiln_loading_rules", "kiln_constants",
                   "warehouse_sections", "production_orders", "order_positions",
                   "tasks", "batches", "schedule_slots"]:
        try:
            row = db.execute(text(f"SELECT count(*) FROM {table}")).scalar()  # noqa: S608
            counts[table] = row
        except Exception as e:
            counts[table] = f"ERROR: {e}"
    return counts


def _verify_internal_auth(request: Request) -> None:
    """Verify internal endpoint access via ADMIN_IP_ALLOWLIST or X-Internal-Key header.

    In production, requires either:
    - X-Internal-Key header matching OWNER_KEY (for Cloud Scheduler)
    - Client IP in ADMIN_IP_ALLOWLIST
    In dev mode, access is open.
    """
    is_production = bool(
        os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENV", "").lower() == "production"
    )
    if not is_production:
        return  # Open in dev mode

    settings = get_settings()

    # Check X-Internal-Key header — prefer dedicated INTERNAL_API_KEY, fall back to OWNER_KEY
    internal_key = request.headers.get("X-Internal-Key")
    expected_key = os.getenv("INTERNAL_API_KEY") or settings.OWNER_KEY
    if internal_key and expected_key and hmac.compare_digest(internal_key, expected_key):
        return

    # Check IP allowlist
    if settings.ADMIN_IP_ALLOWLIST:
        allowed_ips = {ip.strip() for ip in settings.ADMIN_IP_ALLOWLIST.split(",") if ip.strip()}
        client_ip = request.client.host if request.client else None
        if client_ip and client_ip in allowed_ips:
            return

    logger.warning(
        f"Unauthorized internal endpoint access from {request.client.host if request.client else 'unknown'}"
    )
    raise HTTPException(403, "Forbidden")


# ────────────────────────────────────────────────────────────────
# Backup health (admin-only, queries BackupLog table)
# ────────────────────────────────────────────────────────────────

@router.get("/health/backup")
async def backup_health(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Return backup monitoring data from the backup_logs table.

    Includes:
    - last_backup: most recent backup (any status)
    - last_successful_backup: most recent successful backup
    - total_backups: total count of backup log entries
    - days_since_last_success: number of days since last successful backup
    - warning: true if no successful backup in the last 48 hours
    """
    from api.models import BackupLog
    import shutil

    now = datetime.now(timezone.utc)

    # Total count
    total_backups = db.query(sa_func.count(BackupLog.id)).scalar() or 0

    # Last backup (any status)
    last_backup = (
        db.query(BackupLog)
        .order_by(BackupLog.started_at.desc())
        .first()
    )

    # Last successful backup
    last_success = (
        db.query(BackupLog)
        .filter(BackupLog.status == "success")
        .order_by(BackupLog.completed_at.desc())
        .first()
    )

    # Calculate days since last success
    days_since_success = None
    warning = False
    if last_success and last_success.completed_at:
        completed = last_success.completed_at
        if completed.tzinfo is None:
            completed = completed.replace(tzinfo=timezone.utc)
        delta = now - completed
        days_since_success = round(delta.total_seconds() / 86400, 1)
        if delta > timedelta(hours=48):
            warning = True
    elif total_backups > 0:
        # Backups exist but none succeeded
        warning = True

    def _backup_to_dict(entry):
        if not entry:
            return None
        return {
            "id": str(entry.id),
            "started_at": entry.started_at.isoformat() if entry.started_at else None,
            "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
            "status": entry.status,
            "file_size_bytes": entry.file_size_bytes,
            "s3_key": entry.s3_key,
            "error_message": entry.error_message,
            "backup_type": entry.backup_type,
        }

    return {
        "total_backups": total_backups,
        "last_backup": _backup_to_dict(last_backup),
        "last_successful_backup": _backup_to_dict(last_success),
        "days_since_last_success": days_since_success,
        "warning": warning,
        "pg_dump_available": shutil.which("pg_dump") is not None,
        "s3_configured": bool(os.getenv("S3_BACKUP_BUCKET", "")),
    }


# ────────────────────────────────────────────────────────────────
# Manual backup trigger (admin-only)
# ────────────────────────────────────────────────────────────────

@router.post("/admin/backup")
async def trigger_manual_backup(
    background_tasks: BackgroundTasks,
    current_user=Depends(require_admin),
):
    """Trigger a database backup immediately (runs in background).

    Returns the backup_log id for status tracking via GET /api/health/backup.
    """
    from api.scheduler import _create_backup_log

    # Pre-create the log entry so we can return its ID immediately
    backup_log_id = _create_backup_log(backup_type="manual")

    async def _run_manual_backup():
        """Wrapper that runs the backup using the pre-created log entry."""
        from api.scheduler import _finish_backup_log, _send_backup_telegram_alert
        import shutil
        import subprocess
        from urllib.parse import urlparse

        # We duplicate the core logic but reuse the existing log entry.
        # This avoids creating a double log — the pre-created entry is updated.
        import os
        from datetime import datetime as dt, timezone as tz

        global_status_ref = None  # we update _last_backup_status via the module
        from api import scheduler as sched_mod

        is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT"))
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            _finish_backup_log(backup_log_id, status="failed", error="DATABASE_URL not set")
            _send_backup_telegram_alert("Manual backup: DATABASE_URL not set")
            return

        if not shutil.which("pg_dump"):
            _finish_backup_log(backup_log_id, status="failed",
                               error="pg_dump not found in PATH")
            _send_backup_telegram_alert("Manual backup: pg_dump not found")
            return

        s3_bucket = os.getenv("S3_BACKUP_BUCKET", "")
        if is_railway and not s3_bucket:
            _finish_backup_log(backup_log_id, status="failed",
                               error="S3_BACKUP_BUCKET not configured")
            return

        backup_file = None
        try:
            parsed = urlparse(database_url)
            pg_env = {**os.environ, "PGPASSWORD": parsed.password or ""}
            host = parsed.hostname or "localhost"
            port = str(parsed.port or 5432)
            dbname = (parsed.path or "/moonjar").lstrip("/")
            user = parsed.username or "postgres"

            backup_dir = "/tmp/moonjar_backups"
            os.makedirs(backup_dir, exist_ok=True)
            ts = dt.now(tz.utc).strftime("%Y-%m-%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"moonjar_manual_{ts}.dump")

            cmd = [
                "pg_dump", "-h", host, "-p", port, "-U", user, "-d", dbname,
                "--no-owner", "--no-privileges", "--format=custom", "-f", backup_file,
            ]
            result = subprocess.run(cmd, env=pg_env, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                error_msg = f"pg_dump exit code {result.returncode}: {result.stderr[:500]}"
                _finish_backup_log(backup_log_id, status="failed", error=error_msg)
                _send_backup_telegram_alert(f"Manual backup: {error_msg}")
                sched_mod._last_backup_status = {
                    "status": "error", "error": error_msg,
                    "timestamp": dt.now(tz.utc).isoformat(),
                }
                return

            file_size_bytes = os.path.getsize(backup_file)
            file_size_mb = file_size_bytes / (1024 * 1024)

            s3_uploaded = False
            s3_key = None
            if s3_bucket:
                try:
                    import boto3
                    s3_client = boto3.client(
                        "s3",
                        region_name=os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1"),
                    )
                    s3_key = f"moonjar-backups/{dt.now(tz.utc).strftime('%Y-%m-%d')}/moonjar_manual_{ts}.dump"
                    s3_client.upload_file(backup_file, s3_bucket, s3_key)
                    s3_uploaded = True
                except Exception as e:
                    if is_railway:
                        _finish_backup_log(backup_log_id, status="failed",
                                           error=f"S3 upload failed: {e}",
                                           file_size_bytes=file_size_bytes)
                        return

            _finish_backup_log(
                backup_log_id, status="success",
                file_size_bytes=file_size_bytes,
                s3_key=f"s3://{s3_bucket}/{s3_key}" if s3_uploaded else None,
            )
            sched_mod._last_backup_status = {
                "status": "ok",
                "timestamp": dt.now(tz.utc).isoformat(),
                "file_size_mb": round(file_size_mb, 1),
                "s3_uploaded": s3_uploaded,
                "s3_key": f"s3://{s3_bucket}/{s3_key}" if s3_uploaded else None,
            }
        except Exception as e:
            _finish_backup_log(backup_log_id, status="failed", error=str(e)[:2000])
            _send_backup_telegram_alert(f"Manual backup exception: {e}")
        finally:
            if is_railway and backup_file and os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                except OSError:
                    pass

    background_tasks.add_task(_run_manual_backup)

    return {
        "message": "Backup started",
        "backup_id": str(backup_log_id) if backup_log_id else None,
    }


# ────────────────────────────────────────────────────────────────
# Internal status polling
# ────────────────────────────────────────────────────────────────

@router.get("/internal/poll-pms-status")
async def poll_pms_status(request: Request, db: Session = Depends(get_db)):
    """
    Cloud Scheduler keep-alive / status polling endpoint.
    Called every 30 min by GCP Scheduler to:
    - Keep Cloud Run instance warm
    - Verify DB connectivity
    - Return basic system health metrics

    Protected by X-Internal-Key header or IP allowlist in production.
    """
    _verify_internal_auth(request)

    try:
        # Quick DB connectivity check
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "service": "moonjar-pms",
        "db": "connected" if db_ok else "unreachable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
