from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID


# ── Ticket ──────────────────────────────────────────────

class TicketBase(BaseModel):
    client_guid: str
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    segment: str = "Mass"
    description: Optional[str] = None
    attachments: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = None


class TicketOut(TicketBase):
    id: UUID
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: str
    created_at: datetime
    ai_analysis: Optional["AIAnalysisOut"] = None
    distribution: Optional["DistributionOut"] = None

    class Config:
        from_attributes = True


# ── AI Analysis ─────────────────────────────────────────

class AIAnalysisOut(BaseModel):
    id: UUID
    ticket_id: UUID
    type: str
    tonality: str
    priority: int
    language: str
    summary: Optional[str] = None
    geo_latitude: Optional[float] = None
    geo_longitude: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NLPRequest(BaseModel):
    text: str
    address: str


class NLPResponse(BaseModel):
    type: str
    tonality: str
    priority: int
    language: str
    summary: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    nearest_office: Optional[str] = None


# ── Manager ─────────────────────────────────────────────

class ManagerOut(BaseModel):
    id: UUID
    full_name: str
    position: str
    skills: List[str]
    business_unit_id: Optional[UUID] = None
    current_load: int
    business_unit_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Business Unit ───────────────────────────────────────

class BusinessUnitOut(BaseModel):
    id: UUID
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True


# ── Distribution ────────────────────────────────────────

class DistributionOut(BaseModel):
    id: UUID
    ticket_id: UUID
    ai_analysis_id: Optional[UUID] = None
    manager_id: UUID
    reason: Optional[str] = None
    assigned_at: datetime
    manager_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Stats ───────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_tickets: int
    distributed_tickets: int
    pending_tickets: int
    avg_priority: float
    type_distribution: dict
    tonality_distribution: dict
    language_distribution: dict
    manager_load: List[dict]
    office_distribution: dict


# Rebuild forward refs
TicketOut.model_rebuild()
