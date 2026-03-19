import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    industry = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    company_size = Column(Integer, nullable=True)
    tags = Column(Text, default="[]")  # JSON array as string
    email = Column(String(200), nullable=True)
    stage = Column(String(50), default="new_lead")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    activities = relationship("Activity", back_populates="lead", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="lead", cascade="all, delete-orphan")

    def get_tags(self) -> list[str]:
        try:
            return json.loads(self.tags) if self.tags else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tags(self, tags: list[str]):
        self.tags = json.dumps(tags)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    type = Column(String(50), nullable=False)  # call, email, meeting, note, stage_change
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    lead = relationship("Lead", back_populates="activities")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    due_at = Column(DateTime, nullable=False)
    is_done = Column(Boolean, default=False)
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    lead = relationship("Lead", back_populates="reminders")


class EmailCampaign(Base):
    __tablename__ = "email_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    filter_industry = Column(String(100), nullable=True)
    filter_location = Column(String(100), nullable=True)
    filter_stage = Column(String(50), nullable=True)
    status = Column(String(20), default="draft")  # draft, sending, sent, failed
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    sent_at = Column(DateTime, nullable=True)
