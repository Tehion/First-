from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Activity, Lead
from app.schemas import LeadResponse, PipelineSummary, StageUpdate

router = APIRouter(tags=["Pipeline"])


@router.put("/leads/{lead_id}/stage", response_model=LeadResponse)
def update_stage(lead_id: int, data: StageUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_stage = lead.stage
    lead.stage = data.stage.value

    # Auto-log stage change activity
    activity = Activity(
        lead_id=lead.id,
        type="stage_change",
        description=f"Stage changed from '{old_stage}' to '{data.stage.value}'",
    )
    db.add(activity)
    db.commit()
    db.refresh(lead)

    return {
        "id": lead.id,
        "name": lead.name,
        "industry": lead.industry,
        "location": lead.location,
        "company_size": lead.company_size,
        "tags": lead.get_tags(),
        "email": lead.email,
        "stage": lead.stage,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at,
    }


@router.get("/pipeline/summary", response_model=list[PipelineSummary])
def pipeline_summary(db: Session = Depends(get_db)):
    results = db.query(Lead.stage, func.count(Lead.id)).group_by(Lead.stage).all()
    return [{"stage": stage, "count": count} for stage, count in results]
