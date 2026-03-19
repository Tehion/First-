import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.models import Reminder

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def check_due_reminders():
    """Check for due reminders and mark them as notified."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_reminders = (
            db.query(Reminder)
            .filter(Reminder.due_at <= now, Reminder.is_done == False, Reminder.notified == False)
            .all()
        )
        for reminder in due_reminders:
            reminder.notified = True
            logger.info(
                "Reminder due: [%s] '%s' for lead_id=%s",
                reminder.id,
                reminder.title,
                reminder.lead_id,
            )
        if due_reminders:
            db.commit()
            logger.info("Marked %d reminder(s) as notified", len(due_reminders))
    except Exception:
        logger.exception("Error checking reminders")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        check_due_reminders,
        "interval",
        seconds=settings.REMINDER_CHECK_INTERVAL_SECONDS,
        id="check_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Reminder scheduler started (interval=%ds)", settings.REMINDER_CHECK_INTERVAL_SECONDS)


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("Reminder scheduler stopped")
