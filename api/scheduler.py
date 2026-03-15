"""
Moonjar PMS — APScheduler background tasks.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("moonjar.scheduler")
scheduler = AsyncIOScheduler()

# Backup status tracking — updated by daily_database_backup(), read by health endpoint
_last_backup_status: dict | None = None


def get_last_backup_status() -> dict | None:
    """Return the last backup result (used by /api/health/backup endpoint)."""
    return _last_backup_status


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

            # Notify PM
            uf = db.query(UserFactory).join(User).filter(
                UserFactory.factory_id == order.factory_id,
                User.role == UserRole.PRODUCTION_MANAGER.value,
                User.is_active.is_(True),
            ).first()
            if uf:
                notif = Notification(
                    user_id=uf.user_id,
                    factory_id=order.factory_id,
                    type=NotificationType.ALERT,
                    title=title,
                    message=f"Client: {order.client}, Deadline: {order.final_deadline}",
                )
                db.add(notif)

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
        from api.models import MaterialStock, MaterialTransaction
        from sqlalchemy import func as sa_func
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=30)
        stocks = db.query(MaterialStock).filter(MaterialStock.min_balance_auto.is_(True)).all()

        for stock in stocks:
            total_consumed = db.query(
                sa_func.sum(MaterialTransaction.quantity)
            ).filter(
                MaterialTransaction.material_id == stock.material_id,
                MaterialTransaction.factory_id == stock.factory_id,
                MaterialTransaction.type == 'consume',
                MaterialTransaction.created_at >= cutoff,
            ).scalar()

            avg_daily = float(total_consumed or 0) / 30.0
            stock.avg_daily_consumption = abs(avg_daily)
            stock.min_balance_recommended = abs(avg_daily * 7)

        db.commit()
        logger.info("Material balance updated for %d stocks", len(stocks))
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
        from datetime import datetime

        now = datetime.utcnow()
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
        from datetime import datetime

        now = datetime.utcnow()
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
    """Retry failed webhook deliveries."""
    logger.info("Retrying failed webhooks")
    db = _get_db_session()
    try:
        from api.models import SalesWebhookEvent

        failed = db.query(SalesWebhookEvent).filter(
            SalesWebhookEvent.processed.is_(False),
            SalesWebhookEvent.error_message.isnot(None),
        ).limit(10).all()

        # Log for now — full retry logic requires webhook processing service
        if failed:
            logger.info("Found %d failed webhooks to retry", len(failed))

        db.commit()
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

        # Upload to S3
        s3_uploaded = False
        s3_key = None
        if s3_bucket:
            try:
                import boto3
                s3 = boto3.client(
                    "s3",
                    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1"),
                )
                s3_key = f"moonjar-backups/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}/moonjar_{ts}.dump"
                s3.upload_file(backup_file, s3_bucket, s3_key)
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
        # On Railway, always clean up temp file (filesystem is ephemeral anyway)
        if is_railway and backup_file and os.path.exists(backup_file):
            try:
                os.remove(backup_file)
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


async def daily_task_distribution_dispatcher():
    """Hourly dispatcher: send daily task distribution at 21:00 local time per factory.

    Runs every hour at :00.  For each active factory, checks if local time
    is 21:xx.  If so, generates and sends the daily distribution message.
    This approach supports factories across different timezones.
    """
    import pytz
    from datetime import datetime

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
            if local_now.hour == 21:
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

        logger.info("Daily distribution dispatcher: %d factories dispatched", dispatched)
    except Exception as e:
        logger.error("Daily distribution dispatcher failed: %s", e)
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

    # Hourly — webhook retry + daily task distribution per-factory timezone
    scheduler.add_job(hourly_webhook_retry, IntervalTrigger(hours=1), id="webhook_retry")
    scheduler.add_job(
        daily_task_distribution_dispatcher,
        CronTrigger(minute=0),  # Every hour at :00
        id="daily_distribution_dispatcher",
    )

    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs")

    return scheduler
