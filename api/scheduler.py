"""
Moonjar PMS — APScheduler background tasks.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("moonjar.scheduler")
scheduler = AsyncIOScheduler(
    job_defaults={
        "misfire_grace_time": 900,   # 15 min grace period
        "coalesce": True,            # if multiple misfired, run once
        "max_instances": 1,          # no concurrent execution
    },
)

# Backup status tracking — updated by daily_database_backup(), read by health endpoint
_last_backup_status: dict | None = None


def _get_db_session():
    """Get a new database session for scheduled tasks."""
    from api.database import SessionLocal
    return SessionLocal()


def _get_all_factory_ids(db):
    """Get all active factory IDs."""
    from api.models import Factory
    factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
    return [f.id for f in factories]


# --- Job definitions ---

async def daily_sla_check():
    """Check order SLA deadlines, create alerts."""
    logger.info("Running daily SLA check")
    db = _get_db_session()
    try:
        from api.models import ProductionOrder, Notification, User, UserFactory
        from api.enums import OrderStatus, NotificationType, UserRole
        from datetime import date, timedelta

        today = date.today()
        # Find orders with deadline within 3 days or overdue
        orders = db.query(ProductionOrder).filter(
            ProductionOrder.status.in_([
                OrderStatus.IN_PRODUCTION.value,
                OrderStatus.PARTIALLY_READY.value,
            ]),
            ProductionOrder.final_deadline.isnot(None),
            ProductionOrder.final_deadline <= today + timedelta(days=3),
        ).all()

        for order in orders:
            days_left = (order.final_deadline - today).days
            if days_left < 0:
                title = f"OVERDUE: Order {order.order_number} ({abs(days_left)}d late)"
            elif days_left == 0:
                title = f"DUE TODAY: Order {order.order_number}"
            else:
                title = f"Due in {days_left}d: Order {order.order_number}"

            msg = f"Client: {order.client}, Deadline: {order.final_deadline}"

            # Notify PM, CEO, and Owner
            notify_roles = [
                UserRole.PRODUCTION_MANAGER.value,
                UserRole.CEO.value,
                UserRole.OWNER.value,
            ]
            # For truly overdue orders also notify administrator
            if days_left < 0:
                notify_roles.append(UserRole.ADMINISTRATOR.value)

            notified_users: set = set()
            for role in notify_roles:
                users_in_factory = (
                    db.query(UserFactory)
                    .join(User)
                    .filter(
                        UserFactory.factory_id == order.factory_id,
                        User.role == role,
                        User.is_active.is_(True),
                    )
                    .all()
                )
                for uf in users_in_factory:
                    if uf.user_id in notified_users:
                        continue
                    notified_users.add(uf.user_id)
                    db.add(Notification(
                        user_id=uf.user_id,
                        factory_id=order.factory_id,
                        type=NotificationType.ALERT,
                        title=title,
                        message=msg,
                    ))

        db.commit()
        logger.info("SLA check: %d orders flagged", len(orders))
    except Exception as e:
        logger.error("SLA check failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def daily_buffer_health():
    """Recalculate TOC buffer health for all factories."""
    logger.info("Running buffer health check")
    db = _get_db_session()
    try:
        from business.services.buffer_health import calculate_buffer_health
        factory_ids = _get_all_factory_ids(db)
        for fid in factory_ids:
            try:
                calculate_buffer_health(db, fid)
            except Exception as e:
                logger.error("Buffer health failed for factory %s: %s", fid, e)
        db.commit()
        logger.info("Buffer health updated for %d factories", len(factory_ids))
    except Exception as e:
        logger.error("Buffer health job failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def daily_material_balance():
    """Recalculate avg daily consumption and min_balance_recommended."""
    logger.info("Running material balance recalculation")
    db = _get_db_session()
    try:
        from business.services.min_balance import recalculate_min_balance_recommendations

        factory_ids = _get_all_factory_ids(db)
        total_updated = 0
        all_alerts = []

        for fid in factory_ids:
            try:
                result = recalculate_min_balance_recommendations(db, fid)
                total_updated += result.get("updated", 0)
                all_alerts.extend(result.get("alerts", []))
            except Exception as e:
                logger.error("Min balance recalc failed for factory %s: %s", fid, e)

        db.commit()
        logger.info(
            "Material balance updated: %d stocks across %d factories, %d low-stock alerts",
            total_updated, len(factory_ids), len(all_alerts),
        )
    except Exception as e:
        logger.error("Material balance job failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def daily_low_stock_alerts():
    """Generate alerts for materials below min_balance."""
    logger.info("Running low stock alert generation")
    db = _get_db_session()
    try:
        from api.models import Material, MaterialStock, Notification, User, UserFactory
        from api.enums import NotificationType, UserRole

        low_stock = db.query(MaterialStock, Material).join(
            Material, MaterialStock.material_id == Material.id
        ).filter(
            MaterialStock.balance < MaterialStock.min_balance,
        ).all()

        for stock, mat in low_stock:
            uf = db.query(UserFactory).join(User).filter(
                UserFactory.factory_id == stock.factory_id,
                User.role.in_([UserRole.PURCHASER.value, UserRole.PRODUCTION_MANAGER.value]),
                User.is_active.is_(True),
            ).first()
            if uf:
                notif = Notification(
                    user_id=uf.user_id,
                    factory_id=stock.factory_id,
                    type=NotificationType.STOCK_SHORTAGE,
                    title=f"Low stock: {mat.name}",
                    message=(
                        f"Balance: {stock.balance} {mat.unit}, "
                        f"Min: {stock.min_balance} {mat.unit}"
                    ),
                )
                db.add(notif)

        db.commit()
        logger.info("Low stock alerts: %d stocks flagged", len(low_stock))
    except Exception as e:
        logger.error("Low stock alerts failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def daily_overdue_tasks():
    """Flag overdue task assignments."""
    logger.info("Running overdue tasks check")
    db = _get_db_session()
    try:
        from api.models import Task, Notification
        from api.enums import TaskStatus, NotificationType
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        overdue = db.query(Task).filter(
            Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]),
            Task.due_at.isnot(None),
            Task.due_at < now,
        ).all()

        for task in overdue:
            if task.assigned_to:
                notif = Notification(
                    user_id=task.assigned_to,
                    factory_id=task.factory_id,
                    type=NotificationType.ALERT,
                    title=f"Overdue task: {task.description or task.type}",
                    message=f"Due: {task.due_at.strftime('%Y-%m-%d %H:%M')}",
                )
                db.add(notif)

        db.commit()
        logger.info("Overdue tasks: %d flagged", len(overdue))
    except Exception as e:
        logger.error("Overdue tasks check failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def cleanup_expired_sessions():
    """Remove expired active sessions."""
    logger.info("Cleaning up expired sessions")
    db = _get_db_session()
    try:
        from api.models import ActiveSession
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        deleted = db.query(ActiveSession).filter(
            ActiveSession.expires_at < now,
        ).delete()

        db.commit()
        logger.info("Cleaned up %d expired sessions", deleted)
    except Exception as e:
        logger.error("Session cleanup failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def daily_analytics_snapshot():
    """Take daily snapshot: update defect coefficients + buffer health."""
    logger.info("Taking analytics snapshot")
    db = _get_db_session()
    try:
        from business.services.defect_coefficient import update_stone_defect_coefficient
        from business.services.buffer_health import calculate_buffer_health

        factory_ids = _get_all_factory_ids(db)
        for fid in factory_ids:
            try:
                update_stone_defect_coefficient(db, fid)
            except Exception as e:
                logger.error("Defect coefficient update failed for %s: %s", fid, e)
            try:
                calculate_buffer_health(db, fid)
            except Exception as e:
                logger.error("Buffer health update failed for %s: %s", fid, e)

        db.commit()
        logger.info("Analytics snapshot done for %d factories", len(factory_ids))
    except Exception as e:
        logger.error("Analytics snapshot failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def weekly_min_balance_recalc():
    """Recalculate min_balance for auto-managed materials."""
    logger.info("Running weekly min_balance recalculation")
    db = _get_db_session()
    try:
        from api.models import MaterialStock

        stocks = db.query(MaterialStock).filter(
            MaterialStock.min_balance_auto.is_(True),
        ).all()

        for stock in stocks:
            if stock.avg_daily_consumption and float(stock.avg_daily_consumption) > 0:
                new_min = float(stock.avg_daily_consumption) * 7
                stock.min_balance = round(new_min, 3)

        db.commit()
        logger.info("Weekly min_balance recalc: %d stocks", len(stocks))
    except Exception as e:
        logger.error("Weekly min_balance recalc failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def hourly_webhook_retry():
    """Retry failed webhook deliveries (max 3 attempts per event)."""
    logger.info("Retrying failed webhooks")
    db = _get_db_session()
    try:
        from api.models import SalesWebhookEvent
        from business.services.order_intake import process_incoming_order

        MAX_RETRIES = 3

        failed = db.query(SalesWebhookEvent).filter(
            SalesWebhookEvent.processed.is_(False),
            SalesWebhookEvent.permanently_failed.is_(False),
            SalesWebhookEvent.error_message.isnot(None),
            SalesWebhookEvent.retry_count < MAX_RETRIES,
        ).order_by(SalesWebhookEvent.created_at).limit(10).all()

        if not failed:
            logger.info("No failed webhooks to retry")
            return

        logger.info("Found %d failed webhooks to retry", len(failed))
        retried = 0
        succeeded = 0
        permanently_failed_count = 0

        for event in failed:
            event.retry_count = (event.retry_count or 0) + 1
            try:
                payload = event.payload_json
                order_data = payload.get("order", payload)
                source = payload.get("source", "sales_webhook_retry")

                process_incoming_order(
                    db,
                    payload=order_data,
                    source=source,
                    skip_duplicate_check=False,
                )
                event.processed = True
                event.error_message = None
                db.commit()
                succeeded += 1
                logger.info(
                    "Webhook retry SUCCESS: event_id=%s (attempt %d)",
                    event.event_id, event.retry_count,
                )
            except Exception as e:
                db.rollback()
                event.error_message = f"Retry #{event.retry_count}: {str(e)[:500]}"

                if event.retry_count >= MAX_RETRIES:
                    event.permanently_failed = True
                    permanently_failed_count += 1
                    logger.warning(
                        "Webhook PERMANENTLY FAILED after %d attempts: event_id=%s — %s",
                        event.retry_count, event.event_id, str(e)[:200],
                    )
                else:
                    logger.info(
                        "Webhook retry FAILED (attempt %d/%d): event_id=%s — %s",
                        event.retry_count, MAX_RETRIES, event.event_id, str(e)[:200],
                    )
                db.add(event)
                db.commit()
            retried += 1

        logger.info(
            "Webhook retry complete: %d retried, %d succeeded, %d permanently failed",
            retried, succeeded, permanently_failed_count,
        )

        # Send Telegram alert for permanently failed events
        if permanently_failed_count > 0:
            perm_failed = db.query(SalesWebhookEvent).filter(
                SalesWebhookEvent.permanently_failed.is_(True),
            ).order_by(SalesWebhookEvent.created_at.desc()).limit(5).all()
            alert_lines = [f"[Moonjar PMS] {permanently_failed_count} webhook(s) permanently failed:"]
            for ev in perm_failed:
                alert_lines.append(f"  - {ev.event_id}: {(ev.error_message or '')[:100]}")
            _send_backup_telegram_alert("\n".join(alert_lines))

    except Exception as e:
        logger.error("Webhook retry failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def daily_database_backup(backup_type: str = "scheduled"):
    """Create daily database backup using pg_dump, upload to S3.

    On Railway (ephemeral filesystem), S3 upload is REQUIRED — local files
    vanish on every redeploy.  The function:
    1. Creates a BackupLog entry (status=in_progress)
    2. Checks pg_dump is available
    3. Dumps database to /tmp (custom format)
    4. Uploads to S3 if configured (mandatory on Railway)
    5. Cleans up the local temp file
    6. Updates BackupLog with final status
    7. Sends Telegram alert on failure
    8. Stores result in _last_backup_status for the health endpoint

    Returns the backup_log id (UUID str) for tracking, or None.
    """
    import shutil
    import subprocess
    import os
    from datetime import datetime, timezone
    from urllib.parse import urlparse

    global _last_backup_status

    is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT"))
    logger.info("Starting daily database backup (railway=%s, type=%s)", is_railway, backup_type)

    # --- Create BackupLog entry ---
    backup_log_id = _create_backup_log(backup_type)

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        error_msg = "DATABASE_URL not set"
        _last_backup_status = {
            "status": "error",
            "error": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.error("DATABASE_URL not set — cannot create backup")
        _finish_backup_log(backup_log_id, status="failed", error=error_msg)
        _send_backup_telegram_alert(error_msg)
        return backup_log_id

    # Pre-flight: verify pg_dump is available
    if not shutil.which("pg_dump"):
        error_msg = "pg_dump not found in PATH (install postgresql-client)"
        _last_backup_status = {
            "status": "error",
            "error": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.error("pg_dump not found — ensure postgresql-client is installed (nixpacks.toml)")
        _finish_backup_log(backup_log_id, status="failed", error=error_msg)
        _send_backup_telegram_alert(error_msg)
        return backup_log_id

    s3_bucket = os.getenv("S3_BACKUP_BUCKET", "")
    if is_railway and not s3_bucket:
        error_msg = "S3_BACKUP_BUCKET not configured (required on Railway — ephemeral filesystem)"
        _last_backup_status = {
            "status": "error",
            "error": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.error(
            "S3_BACKUP_BUCKET not configured. "
            "On Railway local files are ephemeral — S3 is REQUIRED for backups."
        )
        _finish_backup_log(backup_log_id, status="failed", error=error_msg)
        _send_backup_telegram_alert(error_msg)
        return backup_log_id

    backup_file = None
    try:
        parsed = urlparse(database_url)
        pg_env = {
            **os.environ,
            "PGPASSWORD": parsed.password or "",
        }
        host = parsed.hostname or "localhost"
        port = str(parsed.port or 5432)
        dbname = (parsed.path or "/moonjar").lstrip("/")
        user = parsed.username or "postgres"

        # Backup directory
        backup_dir = "/tmp/moonjar_backups"
        os.makedirs(backup_dir, exist_ok=True)

        # Filename with timestamp
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"moonjar_{ts}.dump")

        # Run pg_dump (custom format — compressed, supports pg_restore)
        cmd = [
            "pg_dump",
            "-h", host,
            "-p", port,
            "-U", user,
            "-d", dbname,
            "--no-owner",
            "--no-privileges",
            "--format=custom",
            "-f", backup_file,
        ]

        result = subprocess.run(
            cmd,
            env=pg_env,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
        )

        if result.returncode != 0:
            error_msg = f"pg_dump exit code {result.returncode}: {result.stderr[:500]}"
            _last_backup_status = {
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            logger.error("pg_dump failed (exit %d): %s", result.returncode, result.stderr)
            _finish_backup_log(backup_log_id, status="failed", error=error_msg)
            _send_backup_telegram_alert(error_msg)
            return backup_log_id

        file_size_bytes = os.path.getsize(backup_file)
        file_size_mb = file_size_bytes / (1024 * 1024)
        logger.info("pg_dump complete: %s (%.1f MB)", backup_file, file_size_mb)

        # --- Encrypt backup if BACKUP_ENCRYPTION_KEY is set ---
        encrypted = False
        upload_file = backup_file
        encryption_key = os.getenv("BACKUP_ENCRYPTION_KEY", "")
        if encryption_key:
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                import hashlib
                import secrets as secrets_mod

                # Derive a 256-bit key from the passphrase
                derived_key = hashlib.sha256(encryption_key.encode()).digest()
                aesgcm = AESGCM(derived_key)
                nonce = secrets_mod.token_bytes(12)  # 96-bit nonce for AES-GCM

                with open(backup_file, "rb") as f:
                    plaintext = f.read()

                ciphertext = aesgcm.encrypt(nonce, plaintext, None)

                encrypted_file = backup_file + ".enc"
                with open(encrypted_file, "wb") as f:
                    # Format: 12-byte nonce + ciphertext (includes 16-byte auth tag)
                    f.write(nonce + ciphertext)

                encrypted = True
                upload_file = encrypted_file
                enc_size = os.path.getsize(encrypted_file)
                logger.info(
                    "Backup encrypted: %s (%.1f MB)",
                    encrypted_file, enc_size / (1024 * 1024),
                )
            except Exception as e:
                logger.error("Backup encryption failed: %s — uploading unencrypted", e)
                # Fall back to unencrypted upload
                upload_file = backup_file

        # Upload to S3
        s3_uploaded = False
        s3_key = None
        s3_ext = ".dump.enc" if encrypted else ".dump"
        if s3_bucket:
            try:
                import boto3
                s3 = boto3.client(
                    "s3",
                    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1"),
                )
                s3_key = f"moonjar-backups/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}/moonjar_{ts}{s3_ext}"
                s3.upload_file(upload_file, s3_bucket, s3_key)
                s3_uploaded = True
                logger.info("Backup uploaded to s3://%s/%s", s3_bucket, s3_key)
            except Exception as e:
                logger.error("S3 upload FAILED: %s", e)
                if is_railway:
                    # On Railway, S3 failure is critical — local file will vanish
                    error_msg = f"S3 upload failed: {e}"
                    _last_backup_status = {
                        "status": "error",
                        "error": error_msg,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "file_size_mb": round(file_size_mb, 1),
                    }
                    _finish_backup_log(backup_log_id, status="failed", error=error_msg,
                                       file_size_bytes=file_size_bytes)
                    _send_backup_telegram_alert(error_msg)
                    return backup_log_id

        # Success
        _last_backup_status = {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_size_mb": round(file_size_mb, 1),
            "s3_uploaded": s3_uploaded,
            "s3_key": f"s3://{s3_bucket}/{s3_key}" if s3_uploaded else None,
            "local_file": backup_file if not is_railway else None,
            "encrypted": encrypted,
        }
        logger.info(
            "Database backup SUCCESS: %.1f MB, s3=%s",
            file_size_mb, s3_uploaded,
        )
        _finish_backup_log(
            backup_log_id,
            status="success",
            file_size_bytes=file_size_bytes,
            s3_key=f"s3://{s3_bucket}/{s3_key}" if s3_uploaded else None,
        )
        return backup_log_id

    except subprocess.TimeoutExpired:
        error_msg = "pg_dump timed out after 300 seconds"
        _last_backup_status = {
            "status": "error",
            "error": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.error("pg_dump timed out after 300 seconds")
        _finish_backup_log(backup_log_id, status="failed", error=error_msg)
        _send_backup_telegram_alert(error_msg)
        return backup_log_id
    except Exception as e:
        error_msg = str(e)[:2000]
        _last_backup_status = {
            "status": "error",
            "error": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.error("Database backup failed: %s", e)
        _finish_backup_log(backup_log_id, status="failed", error=error_msg)
        _send_backup_telegram_alert(f"Backup exception: {error_msg}")
        return backup_log_id
    finally:
        # Clean up temp files (on Railway filesystem is ephemeral anyway)
        for f in [backup_file, (backup_file + ".enc") if backup_file else None]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass


def _create_backup_log(backup_type: str = "scheduled"):
    """Create a BackupLog entry with status=in_progress. Returns log id or None."""
    db = _get_db_session()
    try:
        from api.models import BackupLog
        entry = BackupLog(status="in_progress", backup_type=backup_type)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry.id
    except Exception as e:
        logger.error("Failed to create BackupLog entry: %s", e)
        db.rollback()
        return None
    finally:
        db.close()


def _finish_backup_log(
    backup_log_id,
    *,
    status: str,
    file_size_bytes: int | None = None,
    s3_key: str | None = None,
    error: str | None = None,
):
    """Update a BackupLog entry with final status."""
    if not backup_log_id:
        return
    db = _get_db_session()
    try:
        from api.models import BackupLog
        from datetime import datetime, timezone

        entry = db.query(BackupLog).filter(BackupLog.id == backup_log_id).first()
        if entry:
            entry.status = status
            entry.completed_at = datetime.now(timezone.utc)
            if file_size_bytes is not None:
                entry.file_size_bytes = file_size_bytes
            if s3_key is not None:
                entry.s3_key = s3_key
            if error is not None:
                entry.error_message = error
            db.commit()
    except Exception as e:
        logger.error("Failed to update BackupLog %s: %s", backup_log_id, e)
        db.rollback()
    finally:
        db.close()


def _get_owner_chat_id() -> str:
    """Get owner chat ID — database first, then env var fallback."""
    import os
    try:
        from api.database import SessionLocal
        from api.models import SystemSetting
        db = SessionLocal()
        try:
            s = db.query(SystemSetting).filter(SystemSetting.key == "telegram_owner_chat_id").first()
            if s and s.value:
                return s.value
        finally:
            db.close()
    except Exception:
        pass
    return os.getenv("TELEGRAM_OWNER_CHAT_ID", "")


def _send_backup_telegram_alert(message: str):
    """Send backup failure alert to Telegram owner chat (fire-and-forget)."""
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = _get_owner_chat_id()
    if not token or not chat_id:
        return
    try:
        import httpx
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"[Moonjar PMS] Backup Alert\n\n{message}",
            },
            timeout=10.0,
        )
    except Exception as e:
        logger.warning("Telegram backup alert failed: %s", e)


async def escalation_check():
    """Check all factories for escalation needs every 15 min."""
    logger.info("Running escalation check")
    db = _get_db_session()
    try:
        from business.services.escalation import check_and_escalate
        factory_ids = _get_all_factory_ids(db)
        total_actions = 0
        for fid in factory_ids:
            try:
                actions = check_and_escalate(db, fid)
                total_actions += len(actions)
            except Exception as e:
                logger.error("Escalation check failed for factory %s: %s", fid, e)
        db.commit()
        if total_actions:
            logger.info("Escalation check: %d actions across %d factories", total_actions, len(factory_ids))
    except Exception as e:
        logger.error("Escalation check failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def morning_deferred_alerts():
    """Send deferred non-kiln alerts at 06:00 Bali time."""
    logger.info("Running morning deferred alerts")
    db = _get_db_session()
    try:
        from business.services.escalation import get_deferred_morning_alerts, is_night_time
        if is_night_time():
            return  # Still night, skip

        factory_ids = _get_all_factory_ids(db)
        for fid in factory_ids:
            try:
                deferred = get_deferred_morning_alerts(db, fid)
                if deferred:
                    logger.info("Factory %s: %d deferred alerts", fid, len(deferred))
            except Exception as e:
                logger.error("Morning alerts failed for factory %s: %s", fid, e)
    except Exception as e:
        logger.error("Morning alerts failed: %s", e)
    finally:
        db.close()


async def daily_task_distribution_dispatcher():
    """Hourly dispatcher: send daily task distribution at 07:00 local time per factory.

    Runs every hour at :00.  For each active factory, checks if local time
    is 07:xx.  If so, generates and sends the daily distribution message
    with TODAY's tasks (morning briefing).
    This approach supports factories across different timezones.
    """
    import pytz
    from datetime import datetime, timezone

    logger.info("Running daily task distribution dispatcher")
    db = _get_db_session()
    try:
        from api.models import Factory
        from business.services.daily_distribution import daily_task_distribution

        factories = db.query(Factory).filter(
            Factory.is_active.is_(True),
            Factory.masters_group_chat_id.isnot(None),
        ).all()
        dispatched = 0

        for factory in factories:
            tz_name = factory.timezone or "Asia/Makassar"
            try:
                tz = pytz.timezone(tz_name)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(
                    "Unknown timezone '%s' for factory %s, using Asia/Makassar",
                    tz_name, factory.name,
                )
                tz = pytz.timezone("Asia/Makassar")

            local_now = datetime.now(tz)

            # Morning briefing at 7:00 AM local
            if local_now.hour == 7:
                logger.info(
                    "Dispatching daily distribution for factory %s (tz=%s, local=%s)",
                    factory.name, tz_name, local_now.strftime("%H:%M"),
                )
                try:
                    daily_task_distribution(db, factory.id)
                    dispatched += 1
                except Exception as e:
                    logger.error(
                        "Daily distribution failed for factory %s: %s",
                        factory.name, e,
                    )

            # Evening summary at 6:00 PM local
            if local_now.hour == 18:
                try:
                    _send_evening_summary(db, factory)
                except Exception as e:
                    logger.error("Evening summary failed for %s: %s", factory.name, e)

        logger.info("Daily distribution dispatcher: %d factories dispatched", dispatched)
    except Exception as e:
        logger.error("Daily distribution dispatcher failed: %s", e)
    finally:
        db.close()


def _send_evening_summary(db, factory):
    """Send end-of-day summary to factory team."""
    from api.models import OrderPosition, ProductionOrder, UserStreak, DailyChallenge
    from api.enums import PositionStatus, OrderStatus
    from business.services.notifications import send_telegram_message, get_forum_topic
    from datetime import datetime as dt_cls, date as date_cls, time as time_cls, timezone as tz_cls

    today = date_cls.today()
    today_start = dt_cls.combine(today, time_cls.min).replace(tzinfo=tz_cls.utc)

    # Count positions processed today
    done_statuses = [
        PositionStatus.GLAZED.value, PositionStatus.FIRED.value,
        PositionStatus.TRANSFERRED_TO_SORTING.value, PositionStatus.PACKED.value,
        PositionStatus.QUALITY_CHECK_DONE.value, PositionStatus.READY_FOR_SHIPMENT.value,
        PositionStatus.SHIPPED.value,
    ]
    done_today = db.query(func.count(OrderPosition.id)).filter(
        OrderPosition.factory_id == factory.id,
        OrderPosition.updated_at >= today_start,
        OrderPosition.status.in_(done_statuses),
    ).scalar() or 0

    # Orders shipped today
    shipped = db.query(func.count(ProductionOrder.id)).filter(
        ProductionOrder.factory_id == factory.id,
        ProductionOrder.status == OrderStatus.SHIPPED.value,
        ProductionOrder.updated_at >= today_start,
    ).scalar() or 0

    # Streak
    streak = db.query(UserStreak).filter(
        UserStreak.factory_id == factory.id,
        UserStreak.streak_type == "zero_defects",
    ).first()
    streak_days = streak.current_streak if streak else 0

    # Daily challenge
    challenge = db.query(DailyChallenge).filter(
        DailyChallenge.factory_id == factory.id,
        DailyChallenge.challenge_date == today,
    ).first()
    challenge_text = ""
    if challenge:
        status = "✅ Completed!" if challenge.completed else f"❌ {challenge.actual_value or 0}/{challenge.target_value}"
        challenge_text = f"\n🎯 Challenge: {status}"

    # Build multi-language message based on factory timezone (Bali = id)
    msgs = {
        "en": (
            f"🌙 *Day Complete!* — {factory.name}\n\n"
            f"✅ Positions processed: {done_today}\n"
            f"📦 Orders shipped: {shipped}\n"
            f"🔥 Zero defect streak: {streak_days} days\n"
            f"{challenge_text}\n\n"
            f"Great work today! See you tomorrow 💪"
        ),
        "id": (
            f"🌙 *Hari Selesai!* — {factory.name}\n\n"
            f"✅ Posisi diproses: {done_today}\n"
            f"📦 Pesanan dikirim: {shipped}\n"
            f"🔥 Streak tanpa cacat: {streak_days} hari\n"
            f"{challenge_text}\n\n"
            f"Kerja bagus hari ini! Sampai jumpa besok 💪"
        ),
        "ru": (
            f"🌙 *День завершён!* — {factory.name}\n\n"
            f"✅ Обработано позиций: {done_today}\n"
            f"📦 Отгружено заказов: {shipped}\n"
            f"🔥 Серия без дефектов: {streak_days} дн.\n"
            f"{challenge_text}\n\n"
            f"Отличная работа! До завтра 💪"
        ),
    }
    # Use factory default language, or Indonesian for Bali
    factory_lang = "id" if "bali" in (factory.name or "").lower() else "en"
    msg = msgs.get(factory_lang, msgs["en"])

    # Send to masters group
    if factory.masters_group_chat_id:
        send_telegram_message(int(factory.masters_group_chat_id), msg, parse_mode="Markdown")

    # Send to forum #daily-briefing
    forum_group, daily_topic = get_forum_topic("daily")
    if forum_group:
        send_telegram_message(forum_group, msg, parse_mode="Markdown", message_thread_id=daily_topic)

    logger.info("Evening summary sent for %s: %d done, %d shipped", factory.name, done_today, shipped)


async def stone_waste_weekly_report():
    """Weekly stone waste report — Monday 09:00 Bali (01:00 UTC)."""
    logger.info("Running weekly stone waste report")
    db = _get_db_session()
    try:
        from api.models import Factory, User
        from api.enums import UserRole
        from business.services.stone_reservation import get_weekly_stone_waste_report
        from business.services.notifications import create_notification

        factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
        for factory in factories:
            try:
                report = get_weekly_stone_waste_report(db, factory.id)
                if report and report.get("total_waste_sqm", 0) > 0:
                    pms = db.query(User).filter(
                        User.role == UserRole.PRODUCTION_MANAGER.value,
                        User.is_active.is_(True),
                    ).all()
                    for pm in pms:
                        create_notification(
                            db,
                            user_id=pm.id,
                            type="stone_waste",
                            title=f"Weekly Stone Waste Report — {factory.name}",
                            message=(
                                f"Total waste: {report['total_waste_sqm']:.2f} sqm, "
                                f"compensation: {report.get('total_compensation_idr', 0):,.0f} IDR"
                            ),
                            factory_id=factory.id,
                        )
                    db.commit()
            except Exception as e:
                logger.warning("Stone waste report failed for factory %s: %s", factory.id, e)
                db.rollback()
    except Exception as e:
        logger.error("Stone waste weekly report failed: %s", e)
    finally:
        db.close()


async def check_pending_service_blocks_job():
    """Daily check: re-evaluate service blocking for positions that now have glazing dates."""
    logger.info("Running pending service blocks check")
    db = _get_db_session()
    try:
        from api.models import Factory
        from business.services.service_blocking import check_pending_service_blocks

        factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
        for factory in factories:
            try:
                result = check_pending_service_blocks(db, factory.id)
                blocked_count = result.get("blocked", 0) if isinstance(result, dict) else 0
                if blocked_count > 0:
                    logger.info("Service blocking: %d positions blocked for factory %s", blocked_count, factory.id)
                db.commit()
            except Exception as e:
                logger.warning("Service blocking check failed for factory %s: %s", factory.id, e)
                db.rollback()
    except Exception as e:
        logger.error("Pending service blocks check failed: %s", e)
    finally:
        db.close()


async def anomaly_detection_job():
    """Every 2 hours: run anomaly detection for all factories."""
    logger.info("Running anomaly detection")
    db = _get_db_session()
    try:
        from business.services.anomaly_detection import run_all_anomaly_checks, create_anomaly_alerts

        factory_ids = _get_all_factory_ids(db)
        total_anomalies = 0
        total_alerts = 0

        for fid in factory_ids:
            try:
                anomalies = run_all_anomaly_checks(db, fid)
                if anomalies:
                    total_anomalies += len(anomalies)
                    # Only create alerts for critical anomalies to avoid spam
                    critical = [a for a in anomalies if a.severity == "critical"]
                    if critical:
                        alerts = create_anomaly_alerts(db, critical)
                        total_alerts += alerts
                db.commit()
            except Exception as e:
                logger.error("Anomaly detection failed for factory %s: %s", fid, e)
                db.rollback()

        logger.info(
            "Anomaly detection complete: %d anomalies, %d alerts across %d factories",
            total_anomalies, total_alerts, len(factory_ids),
        )
    except Exception as e:
        logger.error("Anomaly detection job failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def repair_sla_monitor():
    """Every 30 min: check repair positions for SLA breaches (24h limit)."""
    logger.info("Running repair SLA monitor")
    db = _get_db_session()
    try:
        from business.services.repair_monitoring import check_repair_sla

        factory_ids = _get_all_factory_ids(db)
        for fid in factory_ids:
            try:
                escalated = check_repair_sla(db, fid)
                if escalated:
                    logger.info("Repair SLA: %d positions escalated for factory %s", len(escalated), fid)
                db.commit()
            except Exception as e:
                logger.warning("Repair SLA check failed for factory %s: %s", fid, e)
                db.rollback()
    except Exception as e:
        logger.error("Repair SLA monitor failed: %s", e)
    finally:
        db.close()


async def monthly_retention_cleanup():
    """Monthly data retention cleanup per docs/DATA_RETENTION_POLICY.md."""
    logger.info("Running monthly retention cleanup")
    db = _get_db_session()
    try:
        from api.retention import run_retention_cleanup
        results = await run_retention_cleanup(db)
        logger.info("Retention cleanup results: %s", results)
    except Exception as e:
        logger.error("Retention cleanup failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def monthly_holiday_check():
    """Check factory calendars have all Indonesian holidays. Runs 1st of month."""
    db = _get_db_session()
    try:
        from scripts.check_holidays import NATIONAL_HOLIDAYS_2026, BALINESE_HOLIDAYS_2026
        from api.models import FactoryCalendar, Factory
        from datetime import date as dt_date
        from sqlalchemy import select

        year = dt_date.today().year
        factories = db.execute(select(Factory).where(Factory.is_active.is_(True))).scalars().all()

        for factory in factories:
            existing = db.execute(
                select(FactoryCalendar)
                .where(FactoryCalendar.factory_id == factory.id)
                .where(FactoryCalendar.date >= dt_date(year, 1, 1))
                .where(FactoryCalendar.date <= dt_date(year, 12, 31))
            ).scalars().all()
            existing_dates = {str(e.date) for e in existing}

            holidays = list(NATIONAL_HOLIDAYS_2026)
            if "bali" in factory.name.lower():
                holidays += list(BALINESE_HOLIDAYS_2026)

            missing = [(d, n) for d, n in holidays if d not in existing_dates]
            if missing:
                logger.warning(
                    "Factory %s missing %d holidays: %s",
                    factory.name, len(missing),
                    ", ".join(f"{d} ({n})" for d, n in missing[:5]),
                )
                # Auto-add missing holidays
                for d_str, name in missing:
                    try:
                        entry = FactoryCalendar(
                            factory_id=factory.id,
                            date=dt_date.fromisoformat(d_str),
                            reason=name,
                            is_holiday=True,
                            source="auto_check",
                        )
                        db.add(entry)
                    except Exception:
                        pass  # skip duplicates
                db.commit()
                logger.info("Auto-added %d missing holidays for %s", len(missing), factory.name)
            else:
                logger.info("Factory %s: all holidays present (%d entries)", factory.name, len(existing))
    except Exception as e:
        logger.error("Holiday check failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def daily_overdue_purchase_check():
    """Daily check for overdue purchase orders — notify relevant users."""
    logger.info("Running overdue purchase check")
    db = _get_db_session()
    try:
        from business.services.purchaser_lifecycle import check_and_notify_overdue
        check_and_notify_overdue(db)
        db.commit()
        logger.info("Overdue purchase check completed")
    except Exception as e:
        logger.error("Overdue purchase check failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def weekly_purchase_consolidation():
    """Weekly auto-consolidation of purchase requests per factory."""
    logger.info("Running weekly purchase consolidation")
    db = _get_db_session()
    try:
        from api.models import Factory
        from business.services.purchase_consolidation import auto_consolidate_on_schedule

        factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
        for factory in factories:
            try:
                auto_consolidate_on_schedule(db, factory.id)
                db.commit()
            except Exception as e:
                logger.error("Purchase consolidation failed for factory %s: %s", factory.id, e)
                db.rollback()

        logger.info("Purchase consolidation completed for %d factories", len(factories))
    except Exception as e:
        logger.error("Weekly purchase consolidation failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def weekly_summary_dispatcher():
    """Weekly summary: send to PM + CEO for all active factories.

    Runs Sunday 20:00 UTC (Monday 04:00 Bali).
    """
    logger.info("Running weekly summary dispatcher")
    db = _get_db_session()
    try:
        from api.models import Factory
        from business.services.weekly_summary import send_weekly_summary

        factories = db.query(Factory).filter(Factory.is_active.is_(True)).all()
        total_sent = 0
        for factory in factories:
            try:
                sent = send_weekly_summary(db, factory.id)
                total_sent += sent
            except Exception as e:
                logger.error("Weekly summary failed for factory %s: %s", factory.name, e)

        logger.info("Weekly summary dispatched: %d messages across %d factories", total_sent, len(factories))
    except Exception as e:
        logger.error("Weekly summary dispatcher failed: %s", e)
    finally:
        db.close()


async def daily_tps_calibration():
    """Run TPS auto-calibration for all factories. Adjusts production speeds based on EMA of actual data."""
    logger.info("Running daily TPS calibration")
    db = _get_db_session()
    try:
        from business.services.tps_calibration import run_calibration
        from business.services.notifications import send_telegram_to_role

        factory_ids = _get_all_factory_ids(db)
        for fid in factory_ids:
            try:
                suggestions = run_calibration(db, fid, auto_apply=True)
                db.commit()

                if suggestions:
                    applied = [s for s in suggestions if s.get("applied")]
                    pending = [s for s in suggestions if not s.get("applied")]

                    lines = []
                    for s in applied:
                        lines.append(
                            f"  {s['step_name']}: {s['current_rate']} -> {s['suggested_rate']} "
                            f"{s.get('productivity_unit', '')}\n"
                            f"    (fact {s['data_points']}d: {s['ema_value']}, drift: {s['drift_percent']:+.1f}%)"
                        )
                    for s in pending:
                        lines.append(
                            f"  {s['step_name']}: drift {s['drift_percent']:+.1f}% (needs approval)"
                        )

                    from api.models import Factory
                    factory = db.query(Factory).filter(Factory.id == fid).first()
                    msg = (
                        f"TPS Auto-Calibration — {factory.name if factory else fid}\n\n"
                        + "\n".join(lines)
                    )
                    try:
                        send_telegram_to_role(
                            db, fid,
                            roles=["production_manager", "owner"],
                            message=msg,
                        )
                    except Exception as tg_err:
                        logger.warning("TPS calibration Telegram failed: %s", tg_err)

            except Exception as e:
                logger.error("TPS calibration failed for factory %s: %s", fid, e)
                db.rollback()
    finally:
        db.close()
    logger.info("Daily TPS calibration complete")


async def daily_streak_update():
    """Update streaks, evaluate daily challenges, and update achievements for all factories."""
    logger.info("Running daily streak update")
    db = _get_db_session()
    try:
        from datetime import date as date_cls
        from business.services.streaks import (
            update_streaks_for_factory, get_daily_challenge, evaluate_challenge,
        )
        from business.services.achievements import update_achievements_for_user
        from api.models import User, UserFactory
        from api.enums import UserRole

        today = date_cls.today()
        factory_ids = _get_all_factory_ids(db)

        for fid in factory_ids:
            try:
                # Ensure challenge exists for today
                get_daily_challenge(db, fid, today)
                # Update streaks
                update_streaks_for_factory(db, fid, today)
                # Evaluate challenge completion
                evaluate_challenge(db, fid, today)
                db.commit()
            except Exception as e:
                logger.error("Streak update failed for factory %s: %s", fid, e)
                db.rollback()

            # Update achievements for all relevant users in this factory
            try:
                users = db.query(User).join(UserFactory).filter(
                    UserFactory.factory_id == fid,
                    User.is_active.is_(True),
                ).all()
                for user in users:
                    try:
                        update_achievements_for_user(db, user.id)
                    except Exception as e:
                        logger.warning("Achievement update failed for user %s: %s", user.id, e)
                db.commit()
            except Exception as e:
                logger.error("Achievement update failed for factory %s: %s", fid, e)
                db.rollback()

        logger.info("Streak + achievement update completed for %d factories", len(factory_ids))
    except Exception as e:
        logger.error("Daily streak update failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def daily_attendance_check():
    """Check attendance gaps at 7:30 AM Bali time (23:30 UTC).

    For each active factory:
    - Finds working days this month without any attendance records
    - Creates in-app notification for Production Managers
    - Sends Telegram alert to CEO/Owner if 3+ days unfilled
    """
    logger.info("Running daily attendance gap check")
    db = _get_db_session()
    try:
        from business.services.attendance_monitor import process_attendance_gaps

        factory_ids = _get_all_factory_ids(db)
        total_gaps = 0

        for fid in factory_ids:
            try:
                result = process_attendance_gaps(db, fid)
                if result:
                    total_gaps += result["total_unfilled"]
            except Exception as e:
                logger.error("Attendance check failed for factory %s: %s", fid, e)

        logger.info(
            "Attendance check completed: %d total unfilled days across %d factories",
            total_gaps,
            len(factory_ids),
        )
    except Exception as e:
        logger.error("Daily attendance check failed: %s", e)
        db.rollback()
    finally:
        db.close()


# --- Points system resets ---

async def weekly_points_reset():
    """Reset weekly points counter every Monday."""
    logger.info("Running weekly points reset")
    db = _get_db_session()
    try:
        from business.services.points_system import reset_weekly_points
        count = reset_weekly_points(db)
        db.commit()
        logger.info("Weekly points reset done: %d records", count)
    except Exception as e:
        logger.error("Weekly points reset failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def monthly_points_reset():
    """Reset monthly points counter on the 1st of each month."""
    logger.info("Running monthly points reset")
    db = _get_db_session()
    try:
        from business.services.points_system import reset_monthly_points
        count = reset_monthly_points(db)
        db.commit()
        logger.info("Monthly points reset done: %d records", count)
    except Exception as e:
        logger.error("Monthly points reset failed: %s", e)
        db.rollback()
    finally:
        db.close()


# --- Scheduler setup ---

def setup_scheduler():
    """Register all scheduled jobs."""
    # Daily at 21:00 UTC
    scheduler.add_job(daily_sla_check, CronTrigger(hour=21, minute=0), id="sla_check")
    scheduler.add_job(daily_buffer_health, CronTrigger(hour=21, minute=5), id="buffer_health")
    scheduler.add_job(daily_material_balance, CronTrigger(hour=21, minute=10), id="material_balance")
    scheduler.add_job(daily_low_stock_alerts, CronTrigger(hour=21, minute=15), id="low_stock_alerts")
    scheduler.add_job(daily_overdue_tasks, CronTrigger(hour=21, minute=20), id="overdue_tasks")
    scheduler.add_job(daily_analytics_snapshot, CronTrigger(hour=21, minute=30), id="analytics_snapshot")
    scheduler.add_job(daily_database_backup, CronTrigger(hour=22, minute=0), id="daily_backup")

    # Every 6 hours
    scheduler.add_job(cleanup_expired_sessions, IntervalTrigger(hours=6), id="cleanup_sessions")

    # Weekly (Sunday 20:00)
    scheduler.add_job(weekly_min_balance_recalc, CronTrigger(day_of_week="sun", hour=20), id="min_balance_recalc")

    # Every 15 min — escalation check
    scheduler.add_job(escalation_check, IntervalTrigger(minutes=15), id="escalation_check")

    # Morning at 06:05 Bali (22:05 UTC) — deferred alerts (offset from daily_backup at 22:00)
    scheduler.add_job(morning_deferred_alerts, CronTrigger(hour=22, minute=5), id="morning_alerts")

    # Hourly — webhook retry + daily task distribution per-factory timezone
    scheduler.add_job(hourly_webhook_retry, IntervalTrigger(hours=1), id="webhook_retry")
    scheduler.add_job(
        daily_task_distribution_dispatcher,
        CronTrigger(minute=0),  # Every hour at :00
        id="daily_distribution_dispatcher",
    )

    # Weekly Monday 01:00 UTC (09:00 Bali) — stone waste report
    scheduler.add_job(stone_waste_weekly_report, CronTrigger(day_of_week="mon", hour=1, minute=0), id="stone_waste_weekly")

    # Daily 21:35 UTC — check pending service blocks
    scheduler.add_job(check_pending_service_blocks_job, CronTrigger(hour=21, minute=35), id="service_blocks_check")

    # Every 30 min — repair SLA monitor
    scheduler.add_job(repair_sla_monitor, IntervalTrigger(minutes=30), id="repair_sla_monitor")

    # Every 2 hours — anomaly detection
    scheduler.add_job(anomaly_detection_job, IntervalTrigger(hours=2), id="anomaly_detection")

    # Monthly (1st of month at 03:00 UTC) — data retention cleanup
    scheduler.add_job(monthly_retention_cleanup, CronTrigger(day=1, hour=3, minute=0), id="retention_cleanup")

    # Monthly (1st of month at 04:00 UTC) — check factory calendar has all holidays
    scheduler.add_job(monthly_holiday_check, CronTrigger(day=1, hour=4, minute=0), id="holiday_check")

    # Daily at 10:00 UTC — overdue purchase orders check
    scheduler.add_job(daily_overdue_purchase_check, CronTrigger(hour=10, minute=0), id="overdue_purchase_check")

    # Weekly Monday 08:00 UTC — purchase consolidation per factory
    scheduler.add_job(weekly_purchase_consolidation, CronTrigger(day_of_week="mon", hour=8, minute=0), id="purchase_consolidation")

    # Daily 22:30 UTC (06:30 Bali) — streak update + daily challenge evaluation
    scheduler.add_job(daily_streak_update, CronTrigger(hour=22, minute=30), id="streak_update")

    # Weekly Sunday 20:00 UTC (Monday 04:00 Bali) — weekly summary to PM + CEO
    scheduler.add_job(weekly_summary_dispatcher, CronTrigger(day_of_week="sun", hour=20, minute=0), id="weekly_summary")

    # Daily 23:30 UTC (07:30 Bali) — attendance gap check
    scheduler.add_job(daily_attendance_check, CronTrigger(hour=23, minute=30), id="attendance_check")

    # Weekly Monday 00:00 UTC — reset weekly points counter
    scheduler.add_job(weekly_points_reset, CronTrigger(day_of_week="mon", hour=0, minute=0), id="weekly_points_reset")

    # Monthly 1st at 00:05 UTC — reset monthly points counter
    scheduler.add_job(monthly_points_reset, CronTrigger(day=1, hour=0, minute=5), id="monthly_points_reset")

    # Daily 14:00 UTC (22:00 Bali) — TPS auto-calibration
    scheduler.add_job(daily_tps_calibration, CronTrigger(hour=14, minute=0), id="tps_calibration")

    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs")

    return scheduler
