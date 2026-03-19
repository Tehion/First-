from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Lead, Reminder
from app.schemas import ReminderCreate, ReminderResponse, ReminderUpdate

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.post("", response_model=ReminderResponse, status_code=201)
def create_reminder(data: ReminderCreate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == data.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    reminder = Reminder(
        lead_id=data.lead_id,
        title=data.title,
        description=data.description,
        due_at=data.due_at,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("", response_model=list[ReminderResponse])
def list_reminders(
    lead_id: int | None = None,
    upcoming: bool = Query(False, description="Show reminders due in next 24h"),
    overdue: bool = Query(False, description="Show overdue reminders"),
    db: Session = Depends(get_db),
):
    query = db.query(Reminder)

    if lead_id is not None:
        query = query.filter(Reminder.lead_id == lead_id)

    now = datetime.now(timezone.utc)

    if upcoming:
        query = query.filter(
            Reminder.due_at <= now + timedelta(hours=24),
            Reminder.due_at >= now,
            Reminder.is_done == False,
        )
    elif overdue:
        query = query.filter(
            Reminder.due_at < now,
            Reminder.is_done == False,
        )

    return query.order_by(Reminder.due_at.asc()).all()


@router.put("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(reminder_id: int, data: ReminderUpdate, db: Session = Depends(get_db)):
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if data.title is not None:
        reminder.title = data.title
    if data.description is not None:
        reminder.description = data.description
    if data.due_at is not None:
        reminder.due_at = data.due_at
    if data.is_done is not None:
        reminder.is_done = data.is_done

    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: int, db: Session = Depends(get_db)):
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    db.delete(reminder)
    db.commit()
