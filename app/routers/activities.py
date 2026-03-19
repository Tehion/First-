from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Activity, Lead
from app.schemas import ActivityCreate, ActivityResponse

router = APIRouter(tags=["Activities"])


@router.post("/leads/{lead_id}/activities", response_model=ActivityResponse, status_code=201)
def create_activity(lead_id: int, data: ActivityCreate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    activity = Activity(
        lead_id=lead_id,
        type=data.type.value,
        description=data.description,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.get("/leads/{lead_id}/activities", response_model=list[ActivityResponse])
def list_activities(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    activities = (
        db.query(Activity)
        .filter(Activity.lead_id == lead_id)
        .order_by(Activity.created_at.desc())
        .all()
    )
    return activities
