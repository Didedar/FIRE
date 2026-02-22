"""
Tickets API
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.ticket import Ticket
from app.models.distribution import Distribution
from app.models.ai_analysis import AIAnalysis
from app.models.manager import Manager

router = APIRouter(tags=["tickets"])


@router.get("/api/tickets")
@router.get("/api/v1/tickets")
def list_tickets(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    segment: Optional[str] = None,
    ticket_type: Optional[str] = None,
    language: Optional[str] = None,
    city: Optional[str] = None,
    office: Optional[str] = None,
    priority: Optional[int] = Query(None, ge=1, le=10),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Ticket).options(
        joinedload(Ticket.ai_analysis),
        joinedload(Ticket.distribution).joinedload(Distribution.manager),
    )

    if status:
        q = q.filter(Ticket.status == status)
    if segment:
        q = q.filter(Ticket.segment == segment)
    if city:
        q = q.filter(Ticket.city.ilike(f"%{city}%"))
    if search:
        q = q.filter(Ticket.description.ilike(f"%{search}%"))

    # AI analysis-based filters
    if ticket_type or language or priority:
        q = q.join(AIAnalysis, AIAnalysis.ticket_id == Ticket.id, isouter=True)
        if ticket_type:
            q = q.filter(AIAnalysis.type == ticket_type)
        if language:
            q = q.filter(AIAnalysis.language == language)
        if priority:
            q = q.filter(AIAnalysis.priority == priority)

    # Office filter (via distribution → manager → business_unit)
    if office:
        from app.models.business_unit import BusinessUnit
        q = q.join(Distribution, Distribution.ticket_id == Ticket.id, isouter=True)
        q = q.join(Manager, Manager.id == Distribution.manager_id, isouter=True)
        q = q.join(BusinessUnit, BusinessUnit.id == Manager.business_unit_id, isouter=True)
        q = q.filter(BusinessUnit.name.ilike(f"%{office}%"))

    total = q.count()
    tickets = q.order_by(Ticket.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for t in tickets:
        item = {
            "id": str(t.id),
            "client_guid": t.client_guid,
            "gender": t.gender,
            "birth_date": str(t.birth_date) if t.birth_date else None,
            "segment": t.segment,
            "description": t.description,
            "country": t.country,
            "region": t.region,
            "city": t.city,
            "street": t.street,
            "house": t.house,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        if t.ai_analysis:
            item["ai_analysis"] = {
                "type": t.ai_analysis.type,
                "tonality": t.ai_analysis.tonality,
                "priority": t.ai_analysis.priority,
                "language": t.ai_analysis.language,
                "summary": t.ai_analysis.summary,
            }
        else:
            item["ai_analysis"] = None

        if t.distribution and t.distribution.manager:
            item["assigned_manager"] = {
                "id": str(t.distribution.manager.id),
                "full_name": t.distribution.manager.full_name,
                "position": t.distribution.manager.position,
            }
            item["distribution_reason"] = t.distribution.reason
        else:
            item["assigned_manager"] = None
            item["distribution_reason"] = None

        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/api/tickets/{ticket_id}")
@router.get("/api/v1/tickets/{ticket_id}")
def get_ticket(ticket_id: UUID, db: Session = Depends(get_db)):
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.ai_analysis),
            joinedload(Ticket.distribution).joinedload(Distribution.manager),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    result = {
        "id": str(ticket.id),
        "client_guid": ticket.client_guid,
        "gender": ticket.gender,
        "birth_date": str(ticket.birth_date) if ticket.birth_date else None,
        "segment": ticket.segment,
        "description": ticket.description,
        "attachments": ticket.attachments,
        "country": ticket.country,
        "region": ticket.region,
        "city": ticket.city,
        "street": ticket.street,
        "house": ticket.house,
        "latitude": ticket.latitude,
        "longitude": ticket.longitude,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
    }

    if ticket.ai_analysis:
        result["ai_analysis"] = {
            "id": str(ticket.ai_analysis.id),
            "type": ticket.ai_analysis.type,
            "tonality": ticket.ai_analysis.tonality,
            "priority": ticket.ai_analysis.priority,
            "language": ticket.ai_analysis.language,
            "summary": ticket.ai_analysis.summary,
            "geo_latitude": ticket.ai_analysis.geo_latitude,
            "geo_longitude": ticket.ai_analysis.geo_longitude,
        }
    else:
        result["ai_analysis"] = None

    if ticket.distribution:
        result["distribution"] = {
            "id": str(ticket.distribution.id),
            "manager_id": str(ticket.distribution.manager_id),
            "reason": ticket.distribution.reason,
            "assigned_at": ticket.distribution.assigned_at.isoformat() if ticket.distribution.assigned_at else None,
        }
        if ticket.distribution.manager:
            result["distribution"]["manager"] = {
                "full_name": ticket.distribution.manager.full_name,
                "position": ticket.distribution.manager.position,
                "skills": ticket.distribution.manager.skills,
                "current_load": ticket.distribution.manager.current_load,
            }
    else:
        result["distribution"] = None

    return result


@router.delete("/api/tickets/{ticket_id}")
@router.delete("/api/v1/tickets/{ticket_id}")
def delete_ticket(ticket_id: UUID, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Delete related AIAnalysis and Distribution first to avoid foreign key constraints
    db.query(AIAnalysis).filter(AIAnalysis.ticket_id == ticket_id).delete(synchronize_session=False)
    db.query(Distribution).filter(Distribution.ticket_id == ticket_id).delete(synchronize_session=False)

    db.delete(ticket)
    db.commit()
    return {"status": "success", "message": "Ticket deleted"}


@router.delete("/api/tickets")
@router.delete("/api/v1/tickets")
def delete_all_tickets(db: Session = Depends(get_db)):
    # Delete related records first
    db.query(AIAnalysis).delete(synchronize_session=False)
    db.query(Distribution).delete(synchronize_session=False)

    # Delete all tickets
    count = db.query(Ticket).delete(synchronize_session=False)
    db.commit()
    return {"status": "success", "message": f"Deleted {count} tickets"}
