"""
CSV Upload API
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.csv_parser import (
    save_uploaded_file,
    parse_tickets_csv,
    parse_managers_csv,
    parse_business_units_csv,
)

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/tickets")
async def upload_tickets(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    path = save_uploaded_file(content, f"tickets_{file.filename}")

    try:
        count = parse_tickets_csv(path, db)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV parse error: {str(e)}")

    return {"message": f"Uploaded and parsed {count} tickets", "count": count}


@router.post("/managers")
async def upload_managers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    path = save_uploaded_file(content, f"managers_{file.filename}")

    try:
        count = parse_managers_csv(path, db)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV parse error: {str(e)}")

    return {"message": f"Uploaded and parsed {count} managers", "count": count}


@router.post("/business-units")
async def upload_business_units(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    path = save_uploaded_file(content, f"business_units_{file.filename}")

    try:
        count = parse_business_units_csv(path, db)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV parse error: {str(e)}")

    return {"message": f"Uploaded and parsed {count} business units", "count": count}
