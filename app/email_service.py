import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.models import EmailCampaign, Lead

logger = logging.getLogger(__name__)


def is_smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def get_campaign_recipients(db: Session, campaign: EmailCampaign) -> list[str]:
    """Query leads matching campaign filters that have an email."""
    query = db.query(Lead).filter(Lead.email.isnot(None), Lead.email != "")

    if campaign.filter_industry:
        query = query.filter(Lead.industry == campaign.filter_industry)
    if campaign.filter_location:
        query = query.filter(Lead.location == campaign.filter_location)
    if campaign.filter_stage:
        query = query.filter(Lead.stage == campaign.filter_stage)

    return [lead.email for lead in query.all()]


def send_single_email(to: str, subject: str, body: str) -> bool:
    """Send a single email via SMTP. Returns True on success."""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        if settings.SMTP_USE_TLS:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to, msg.as_string())
        server.quit()
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def send_campaign(campaign_id: int):
    """Background task: send emails for a campaign."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        campaign = db.query(EmailCampaign).filter(EmailCampaign.id == campaign_id).first()
        if not campaign:
            logger.error("Campaign %d not found", campaign_id)
            return

        recipients = get_campaign_recipients(db, campaign)
        campaign.status = "sending"
        campaign.total_recipients = len(recipients)
        db.commit()

        sent = 0
        failed = 0
        for email_addr in recipients:
            if send_single_email(email_addr, campaign.subject, campaign.body):
                sent += 1
            else:
                failed += 1

        campaign.sent_count = sent
        campaign.failed_count = failed
        campaign.status = "sent" if sent > 0 else "failed"
        campaign.sent_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("Campaign %d: sent=%d, failed=%d", campaign_id, sent, failed)
    except Exception:
        logger.exception("Error sending campaign %d", campaign_id)
        db.rollback()
    finally:
        db.close()
