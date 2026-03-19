from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.email_service import get_campaign_recipients, is_smtp_configured, send_campaign
from app.models import EmailCampaign
from app.schemas import CampaignCreate, CampaignResponse, PreviewResponse

router = APIRouter(prefix="/emails", tags=["Email Campaigns"])


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
def create_campaign(data: CampaignCreate, db: Session = Depends(get_db)):
    campaign = EmailCampaign(
        subject=data.subject,
        body=data.body,
        filter_industry=data.filter_industry,
        filter_location=data.filter_location,
        filter_stage=data.filter_stage,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/campaigns", response_model=list[CampaignResponse])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(EmailCampaign).order_by(EmailCampaign.created_at.desc()).all()


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(EmailCampaign).filter(EmailCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/campaigns/{campaign_id}/preview", response_model=PreviewResponse)
def preview_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(EmailCampaign).filter(EmailCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    recipients = get_campaign_recipients(db, campaign)
    return {"recipients": recipients, "count": len(recipients)}


@router.post("/campaigns/{campaign_id}/send")
def send_campaign_endpoint(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not is_smtp_configured():
        raise HTTPException(
            status_code=400,
            detail="SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD environment variables.",
        )

    campaign = db.query(EmailCampaign).filter(EmailCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == "sending":
        raise HTTPException(status_code=400, detail="Campaign is already being sent")

    background_tasks.add_task(send_campaign, campaign_id)
    return {"status": "sending", "campaign_id": campaign_id}
