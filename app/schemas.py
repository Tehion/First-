from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr


# --- Enums ---

class LeadStage(str, Enum):
    new_lead = "new_lead"
    contacted = "contacted"
    proposal = "proposal"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"


class ActivityType(str, Enum):
    call = "call"
    email = "email"
    meeting = "meeting"
    note = "note"
    stage_change = "stage_change"


# --- Lead Schemas ---

class LeadCreate(BaseModel):
    name: str
    industry: str | None = None
    location: str | None = None
    company_size: int | None = None
    tags: list[str] = []
    email: str | None = None
    stage: LeadStage = LeadStage.new_lead


class LeadUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    location: str | None = None
    company_size: int | None = None
    tags: list[str] | None = None
    email: str | None = None


class LeadResponse(BaseModel):
    id: int
    name: str
    industry: str | None
    location: str | None
    company_size: int | None
    tags: list[str]
    email: str | None
    stage: str
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class LeadWithActivities(LeadResponse):
    activities: list["ActivityResponse"] = []


# --- Lookalike Schemas ---

class LookalikeSeed(BaseModel):
    industry: str | None = None
    location: str | None = None
    company_size: int | None = None
    tags: list[str] = []


class LookalikeRequest(BaseModel):
    seed: LookalikeSeed | None = None
    seed_lead_id: int | None = None
    limit: int = 5


class LookalikeResult(BaseModel):
    lead: LeadResponse
    score: float


# --- Activity Schemas ---

class ActivityCreate(BaseModel):
    type: ActivityType
    description: str | None = None


class ActivityResponse(BaseModel):
    id: int
    lead_id: int
    type: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Stage Schemas ---

class StageUpdate(BaseModel):
    stage: LeadStage


class PipelineSummary(BaseModel):
    stage: str
    count: int


# --- Reminder Schemas ---

class ReminderCreate(BaseModel):
    lead_id: int
    title: str
    description: str | None = None
    due_at: datetime


class ReminderUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_at: datetime | None = None
    is_done: bool | None = None


class ReminderResponse(BaseModel):
    id: int
    lead_id: int
    title: str
    description: str | None
    due_at: datetime
    is_done: bool
    notified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Email Campaign Schemas ---

class CampaignCreate(BaseModel):
    subject: str
    body: str
    filter_industry: str | None = None
    filter_location: str | None = None
    filter_stage: str | None = None


class CampaignResponse(BaseModel):
    id: int
    subject: str
    body: str
    filter_industry: str | None
    filter_location: str | None
    filter_stage: str | None
    status: str
    total_recipients: int
    sent_count: int
    failed_count: int
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}


class PreviewResponse(BaseModel):
    recipients: list[str]
    count: int
