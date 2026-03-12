"""
Moonjar PMS — APScheduler background tasks.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("moonjar.scheduler")
scheduler = AsyncIOScheduler()


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


async def daily_database_backup():
    """Create daily database backup using pg_dump → local file (rotated 7 days)."""
    import subprocess
    import os
    from datetime import datetime
    from urllib.parse import urlparse

    logger.info("Starting daily database backup")

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        logger.error("DATABASE_URL not set — cannot create backup")
        return

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

        # Filename with date (rotate weekly by using day-of-week)
        day_of_week = datetime.utcnow().strftime("%A")
        backup_file = os.path.join(backup_dir, f"moonjar_{day_of_week}.sql.gz")

        # Remove old backup for this day
        if os.path.exists(backup_file):
            os.remove(backup_file)

        # Run pg_dump
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
            logger.error("pg_dump failed: %s", result.stderr)
            return

        file_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
        logger.info(
            "Database backup created: %s (%.1f MB)",
            backup_file, file_size,
        )

        # Optional: upload to S3 if configured
        s3_bucket = os.getenv("S3_BACKUP_BUCKET", "")
        if s3_bucket:
            try:
                import boto3
                s3 = boto3.client("s3")
                s3_key = f"moonjar-backups/{datetime.utcnow().strftime('%Y-%m-%d')}/moonjar_backup.dump"
                s3.upload_file(backup_file, s3_bucket, s3_key)
                logger.info("Backup uploaded to s3://%s/%s", s3_bucket, s3_key)
            except Exception as e:
                logger.warning("S3 upload failed (backup still on disk): %s", e)

    except Exception as e:
        logger.error("Database backup failed: %s", e)


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

    # Hourly
    scheduler.add_job(hourly_webhook_retry, IntervalTrigger(hours=1), id="webhook_retry")

    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs")

    return scheduler
