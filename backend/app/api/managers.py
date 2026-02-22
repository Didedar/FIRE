"""
Managers API
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.manager import Manager
from app.models.business_unit import BusinessUnit
from app.models.distribution import Distribution

router = APIRouter(tags=["managers"])


@router.get("/api/managers")
@router.get("/api/v1/managers")
def list_managers(db: Session = Depends(get_db)):
    managers = db.query(Manager).options(joinedload(Manager.business_unit)).all()

    items = []
    for m in managers:
        items.append({
            "id": str(m.id),
            "full_name": m.full_name,
            "position": m.position,
            "skills": m.skills or [],
            "business_unit_id": str(m.business_unit_id) if m.business_unit_id else None,
            "business_unit_name": m.business_unit.name if m.business_unit else None,
            "current_load": m.current_load,
        })

    return {"items": items, "total": len(items)}


@router.get("/api/managers/offices")
@router.get("/api/v1/managers/offices")
def list_offices(db: Session = Depends(get_db)):
    offices = db.query(BusinessUnit).all()
    return {
        "items": [
            {
                "id": str(o.id),
                "name": o.name,
                "address": o.address,
                "latitude": o.latitude,
                "longitude": o.longitude,
            }
            for o in offices
        ]
    }


@router.delete("/api/managers/offices/{office_id}")
@router.delete("/api/v1/managers/offices/{office_id}")
def delete_office(office_id: UUID, db: Session = Depends(get_db)):
    office = db.query(BusinessUnit).filter(BusinessUnit.id == office_id).first()
    if not office:
        raise HTTPException(status_code=404, detail="Office not found")

    # Nullify business_unit_id for managers in this office
    db.query(Manager).filter(Manager.business_unit_id == office_id).update({"business_unit_id": None}, synchronize_session=False)

    db.delete(office)
    db.commit()
    return {"status": "success", "message": "Office deleted"}


@router.delete("/api/managers/offices")
@router.delete("/api/v1/managers/offices")
def delete_all_offices(db: Session = Depends(get_db)):
    # Nullify business_unit_id for all managers
    db.query(Manager).update({"business_unit_id": None}, synchronize_session=False)

    count = db.query(BusinessUnit).delete(synchronize_session=False)
    db.commit()
    return {"status": "success", "message": f"Deleted {count} offices"}


@router.delete("/api/managers/{manager_id}")
@router.delete("/api/v1/managers/{manager_id}")
def delete_manager(manager_id: UUID, db: Session = Depends(get_db)):
    manager = db.query(Manager).filter(Manager.id == manager_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")

    # Clear distributions assigned to this manager (or delete distributions)
    db.query(Distribution).filter(Distribution.manager_id == manager_id).delete(synchronize_session=False)

    db.delete(manager)
    db.commit()
    return {"status": "success", "message": "Manager deleted"}


@router.delete("/api/managers")
@router.delete("/api/v1/managers")
def delete_all_managers(db: Session = Depends(get_db)):
    # Clear all distributions since they depend on managers
    db.query(Distribution).delete(synchronize_session=False)

    count = db.query(Manager).delete(synchronize_session=False)
    db.commit()
    return {"status": "success", "message": f"Deleted {count} managers"}
