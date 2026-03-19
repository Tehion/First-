from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Lead
from app.schemas import (
    LeadCreate,
    LeadResponse,
    LeadUpdate,
    LeadWithActivities,
    LookalikeRequest,
    LookalikeResult,
)
from app.scoring import compute_similarity

router = APIRouter(prefix="/leads", tags=["Leads"])


def _lead_to_response(lead: Lead) -> dict:
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


@router.post("", response_model=LeadResponse, status_code=201)
def create_lead(data: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(
        name=data.name,
        industry=data.industry,
        location=data.location,
        company_size=data.company_size,
        email=data.email,
        stage=data.stage.value,
    )
    lead.set_tags(data.tags)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _lead_to_response(lead)


@router.get("", response_model=list[LeadResponse])
def list_leads(
    industry: str | None = None,
    location: str | None = None,
    stage: str | None = None,
    min_size: int | None = None,
    max_size: int | None = None,
    tag: str | None = None,
    q: str | None = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
):
    query = db.query(Lead)
    if industry:
        query = query.filter(Lead.industry == industry)
    if location:
        query = query.filter(Lead.location == location)
    if stage:
        query = query.filter(Lead.stage == stage)
    if min_size is not None:
        query = query.filter(Lead.company_size >= min_size)
    if max_size is not None:
        query = query.filter(Lead.company_size <= max_size)
    if tag:
        query = query.filter(Lead.tags.contains(f'"{tag}"'))
    if q:
        query = query.filter(Lead.name.ilike(f"%{q}%"))

    leads = query.order_by(Lead.created_at.desc()).all()
    return [_lead_to_response(lead) for lead in leads]


@router.get("/{lead_id}", response_model=LeadWithActivities)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    resp = _lead_to_response(lead)
    resp["activities"] = [
        {
            "id": a.id,
            "lead_id": a.lead_id,
            "type": a.type,
            "description": a.description,
            "created_at": a.created_at,
        }
        for a in lead.activities
    ]
    return resp


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: int, data: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if data.name is not None:
        lead.name = data.name
    if data.industry is not None:
        lead.industry = data.industry
    if data.location is not None:
        lead.location = data.location
    if data.company_size is not None:
        lead.company_size = data.company_size
    if data.email is not None:
        lead.email = data.email
    if data.tags is not None:
        lead.set_tags(data.tags)

    db.commit()
    db.refresh(lead)
    return _lead_to_response(lead)


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()


@router.post("/lookalike", response_model=list[LookalikeResult])
def lookalike_search(data: LookalikeRequest, db: Session = Depends(get_db)):
    if data.seed_lead_id:
        seed_lead = db.query(Lead).filter(Lead.id == data.seed_lead_id).first()
        if not seed_lead:
            raise HTTPException(status_code=404, detail="Seed lead not found")
        seed = {
            "industry": seed_lead.industry,
            "location": seed_lead.location,
            "company_size": seed_lead.company_size,
            "tags": seed_lead.get_tags(),
        }
        exclude_id = seed_lead.id
    elif data.seed:
        seed = data.seed.model_dump()
        exclude_id = None
    else:
        raise HTTPException(status_code=400, detail="Provide seed or seed_lead_id")

    leads = db.query(Lead).all()
    results = []
    for lead in leads:
        if exclude_id and lead.id == exclude_id:
            continue
        score = compute_similarity(seed, lead)
        if score > 0:
            results.append({"lead": _lead_to_response(lead), "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[: data.limit]
