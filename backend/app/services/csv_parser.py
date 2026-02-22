"""
CSV Parser Service
Parses Tickets, Managers, and Business Units CSV files and saves to DB.
"""

import os
import shutil
from datetime import datetime
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.models.ticket import Ticket
from app.models.manager import Manager
from app.models.business_unit import BusinessUnit


def ensure_csv_storage():
    os.makedirs(settings.CSV_STORAGE_PATH, exist_ok=True)


def save_uploaded_file(file_bytes: bytes, filename: str) -> str:
    """Save uploaded file to csv_storage and return the path."""
    ensure_csv_storage()
    path = os.path.join(settings.CSV_STORAGE_PATH, filename)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path


def parse_tickets_csv(file_path: str, db: Session) -> int:
    """Parse tickets CSV and insert into DB. Returns count of inserted records."""
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    # Strip trailing whitespace from column names
    df.columns = df.columns.str.strip()

    # Normalize column names
    col_map = {}
    for col in df.columns:
        cl = col.strip().lower()
        if "guid" in cl or "клиент" in cl:
            col_map[col] = "client_guid"
        elif "пол" in cl or "gender" in cl:
            col_map[col] = "gender"
        elif "дата" in cl and "рожд" in cl or "birth" in cl:
            col_map[col] = "birth_date"
        elif "сегмент" in cl or "segment" in cl:
            col_map[col] = "segment"
        elif "описание" in cl or "description" in cl or "текст" in cl:
            col_map[col] = "description"
        elif "вложен" in cl or "attach" in cl:
            col_map[col] = "attachments"
        elif "страна" in cl or "country" in cl:
            col_map[col] = "country"
        elif "область" in cl or "region" in cl or "облас" in cl:
            col_map[col] = "region"
        elif "населен" in cl or "город" in cl or "city" in cl:
            col_map[col] = "city"
        elif "улица" in cl or "street" in cl:
            col_map[col] = "street"
        elif "дом" in cl or "house" in cl:
            col_map[col] = "house"
    
    df = df.rename(columns=col_map)

    count = 0
    for _, row in df.iterrows():
        birth_date = None
        if "birth_date" in row and pd.notna(row.get("birth_date")):
            try:
                birth_date = pd.to_datetime(row["birth_date"]).date()
            except Exception:
                birth_date = None

        ticket = Ticket(
            id=uuid4(),
            client_guid=str(row.get("client_guid", "")),
            gender=str(row.get("gender", "")) if pd.notna(row.get("gender")) else None,
            birth_date=birth_date,
            segment=str(row.get("segment", "Mass")) if pd.notna(row.get("segment")) else "Mass",
            description=str(row.get("description", "")) if pd.notna(row.get("description")) else None,
            attachments=str(row.get("attachments", "")) if pd.notna(row.get("attachments")) else None,
            country=str(row.get("country", "")) if pd.notna(row.get("country")) else None,
            region=str(row.get("region", "")) if pd.notna(row.get("region")) else None,
            city=str(row.get("city", "")) if pd.notna(row.get("city")) else None,
            street=str(row.get("street", "")) if pd.notna(row.get("street")) else None,
            house=str(row.get("house", "")) if pd.notna(row.get("house")) else None,
            status="new",
        )
        db.add(ticket)
        count += 1

    db.commit()
    return count


def parse_managers_csv(file_path: str, db: Session) -> int:
    """Parse managers CSV and insert into DB. Returns count of inserted records."""
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    # Strip trailing whitespace from column names
    df.columns = df.columns.str.strip()

    col_map = {}
    for col in df.columns:
        cl = col.strip().lower()
        if "фио" in cl or "имя" in cl or "name" in cl:
            col_map[col] = "full_name"
        elif "должн" in cl or "position" in cl:
            col_map[col] = "position"
        elif "навык" in cl or "skill" in cl:
            col_map[col] = "skills"
        elif "бизнес" in cl or "офис" in cl or "unit" in cl or "office" in cl:
            col_map[col] = "business_unit"
        elif "кол" in cl or "нагруз" in cl or "load" in cl or "обращен" in cl:
            col_map[col] = "current_load"

    df = df.rename(columns=col_map)

    # Pre-load business units for matching
    bus = db.query(BusinessUnit).all()
    bu_map = {}
    for b in bus:
        bu_map[b.name.strip().lower()] = b.id

    count = 0
    for _, row in df.iterrows():
        skills_raw = str(row.get("skills", "")) if pd.notna(row.get("skills")) else ""
        skills = [s.strip() for s in skills_raw.replace(";", ",").split(",") if s.strip()]

        bu_name = str(row.get("business_unit", "")).strip().lower() if pd.notna(row.get("business_unit")) else ""
        bu_id = bu_map.get(bu_name)

        load_val = 0
        if "current_load" in row and pd.notna(row.get("current_load")):
            try:
                load_val = int(row["current_load"])
            except (ValueError, TypeError):
                load_val = 0

        manager = Manager(
            id=uuid4(),
            full_name=str(row.get("full_name", "")),
            position=str(row.get("position", "")) if pd.notna(row.get("position")) else "",
            skills=skills,
            business_unit_id=bu_id,
            current_load=load_val,
        )
        db.add(manager)
        count += 1

    db.commit()
    return count


def parse_business_units_csv(file_path: str, db: Session) -> int:
    """Parse business units CSV and insert into DB. Returns count of inserted records."""
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    # Strip trailing whitespace from column names
    df.columns = df.columns.str.strip()

    col_map = {}
    for col in df.columns:
        cl = col.strip().lower()
        if "офис" in cl or "name" in cl or "назван" in cl:
            col_map[col] = "name"
        elif "адрес" in cl or "address" in cl:
            col_map[col] = "address"

    df = df.rename(columns=col_map)

    # All 15 Office coordinates (exact from spec)
    OFFICE_COORDS = {
        "актау": (43.6355, 51.1680),
        "актобе": (50.2839, 57.1670),
        "алматы": (43.2380, 76.9458),
        "астана": (51.1694, 71.4491),
        "атырау": (47.1068, 51.9032),
        "караганда": (49.8047, 73.1094),
        "кокшетау": (53.2836, 69.3783),
        "костанай": (53.2144, 63.6246),
        "кызылорда": (44.8488, 65.5093),
        "павлодар": (52.2873, 76.9674),
        "петропавловск": (54.8720, 69.1414),
        "тараз": (42.9000, 71.3667),
        "уральск": (51.2333, 51.3667),
        "усть-каменогорск": (49.9482, 82.6279),
        "шымкент": (42.3154, 69.5967),
    }

    count = 0
    for _, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        address = str(row.get("address", "")) if pd.notna(row.get("address")) else ""

        lat, lon = None, None
        # First try exact match on office name
        name_lower = name.lower()
        if name_lower in OFFICE_COORDS:
            lat, lon = OFFICE_COORDS[name_lower]
        else:
            # Fallback: search in combined string
            search = (name + " " + address).lower()
            for city_name, (clat, clon) in OFFICE_COORDS.items():
                if city_name in search:
                    lat, lon = clat, clon
                    break

        bu = BusinessUnit(
            id=uuid4(),
            name=name,
            address=address,
            latitude=lat,
            longitude=lon,
        )
        db.add(bu)
        count += 1

    db.commit()
    return count
