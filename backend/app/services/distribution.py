"""
Distribution Engine
Implements the cascade of business rules:
1. Geographic filter → nearest office
2. Competency filter → hard skills match
3. Round Robin → balanced assignment
"""

from uuid import uuid4
from collections import defaultdict
from itertools import cycle

from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.manager import Manager
from app.models.business_unit import BusinessUnit
from app.models.ai_analysis import AIAnalysis
from app.models.distribution import Distribution
from app.services.nlp_client import analyze_ticket, load_rag_context
from app.utils.geo import find_nearest_office, haversine


# ━━━ Step 1: Geographic Filter ━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_target_offices(
    ticket: Ticket,
    analysis: AIAnalysis,
    offices: list[BusinessUnit],
) -> list[BusinessUnit]:
    """
    Find the target office(s) for a ticket.
    - If client has geo coords in KZ → nearest office
    - If unknown address or abroad → split 50/50 between Астана & Алматы
    """
    client_lat = analysis.geo_latitude or ticket.latitude
    client_lon = analysis.geo_longitude or ticket.longitude

    office_dicts = [
        {"id": o.id, "name": o.name, "latitude": o.latitude, "longitude": o.longitude}
        for o in offices
        if o.latitude is not None
    ]

    nearest = find_nearest_office(client_lat, client_lon, office_dicts)

    if nearest:
        return [o for o in offices if o.id == nearest["id"]]

    # Fallback: Астана & Алматы
    fallback = []
    for o in offices:
        name_lower = o.name.lower()
        if "астана" in name_lower or "алматы" in name_lower:
            fallback.append(o)
    return fallback if fallback else offices[:2] if len(offices) >= 2 else offices


# ━━━ Step 2: Competency Filter ━━━━━━━━━━━━━━━━━━━━━━━━━

def _filter_by_competency(
    managers: list[Manager],
    segment: str,
    ticket_type: str,
    language: str,
) -> list[Manager]:
    """
    Filter managers by hard skills:
    - VIP/Priority segment → requires VIP skill
    - Смена данных type → requires Глав спец position
    - KZ/ENG language → requires matching skill
    """
    result = list(managers)

    # VIP/Priority filter
    if segment in ("VIP", "Priority"):
        result = [m for m in result if "VIP" in m.skills]

    # Смена данных → Глав спец only
    if ticket_type == "Смена данных":
        result = [m for m in result if "Глав" in m.position]

    # Language skills
    if language == "KZ":
        result = [m for m in result if "KZ" in m.skills]
    elif language == "ENG":
        result = [m for m in result if "ENG" in m.skills]

    return result


# ━━━ Step 3: Round Robin ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _select_round_robin(
    managers: list[Manager],
    rr_state: dict,
) -> Manager | None:
    """
    Select from 2 managers with lowest load, alternating via round robin.
    """
    if not managers:
        return None

    # Sort by current load
    sorted_mgrs = sorted(managers, key=lambda m: m.current_load)
    top_two = sorted_mgrs[:2]

    if len(top_two) == 1:
        return top_two[0]

    # Build a key for RR state
    key = tuple(sorted(str(m.id) for m in top_two))
    if key not in rr_state:
        rr_state[key] = 0

    idx = rr_state[key] % 2
    rr_state[key] += 1

    return top_two[idx]


# ━━━ Main Distribution ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def distribute_tickets(db: Session) -> dict:
    """
    Run the full distribution pipeline:
    1. Get all undistributed tickets
    2. For each: analyze with NLP → find office → filter managers → round robin assign
    Returns stats dict.
    """
    # Load all offices and managers
    offices = db.query(BusinessUnit).all()
    all_managers = db.query(Manager).all()

    # Load RAG context once for the whole batch
    load_rag_context(db)

    # Get undistributed tickets
    distributed_ids = db.query(Distribution.ticket_id).subquery()
    tickets = (
        db.query(Ticket)
        .filter(~Ticket.id.in_(db.query(distributed_ids.c.ticket_id)))
        .all()
    )

    rr_state = {}
    stats = {
        "total": len(tickets),
        "distributed": 0,
        "skipped": 0,
        "errors": [],
    }

    # Track assignments for 50/50 split
    astana_alm_counter = {"астана": 0, "алматы": 0}

    for ticket in tickets:
        try:
            # ── NLP Analysis ──
            address_parts = [
                ticket.country or "",
                ticket.region or "",
                ticket.city or "",
                ticket.street or "",
                ticket.house or "",
            ]
            address_str = ", ".join(p for p in address_parts if p)

            nlp_result = await analyze_ticket(
                text=ticket.description or "",
                address=address_str,
                db_session=db,
                segment=ticket.segment,
            )

            # Save AI analysis
            analysis = AIAnalysis(
                id=uuid4(),
                ticket_id=ticket.id,
                type=nlp_result.type,
                tonality=nlp_result.tonality,
                priority=nlp_result.priority,
                language=nlp_result.language,
                summary=nlp_result.summary,
                geo_latitude=nlp_result.latitude,
                geo_longitude=nlp_result.longitude,
            )
            db.add(analysis)

            # Update ticket geo if we got coords from NLP
            if nlp_result.latitude and nlp_result.longitude:
                ticket.latitude = nlp_result.latitude
                ticket.longitude = nlp_result.longitude
            ticket.status = "analyzed"

            # ── Geographic Filter ──
            target_offices = _get_target_offices(ticket, analysis, offices)

            # For 50/50 fallback: pick the office with fewer assignments
            if len(target_offices) >= 2:
                office_names = [o.name.lower() for o in target_offices]
                has_astana = any("астана" in n for n in office_names)
                has_almaty = any("алматы" in n for n in office_names)
                if has_astana and has_almaty:
                    if astana_alm_counter["астана"] <= astana_alm_counter["алматы"]:
                        target_offices = [o for o in target_offices if "астана" in o.name.lower()]
                        astana_alm_counter["астана"] += 1
                    else:
                        target_offices = [o for o in target_offices if "алматы" in o.name.lower()]
                        astana_alm_counter["алматы"] += 1

            # Collect managers from target offices
            office_ids = {o.id for o in target_offices}
            office_managers = [m for m in all_managers if m.business_unit_id in office_ids]

            # ── Competency Filter ──
            qualified = _filter_by_competency(
                office_managers,
                ticket.segment,
                nlp_result.type,
                nlp_result.language,
            )

            # Fallback 1: if no qualified managers in target office, search all offices
            if not qualified:
                qualified = _filter_by_competency(
                    all_managers,
                    ticket.segment,
                    nlp_result.type,
                    nlp_result.language,
                )

            # Fallback 2: if STILL no qualified managers, just pick ANY manager to avoid skipping
            if not qualified:
                qualified = all_managers

            # ── Round Robin ──
            assigned = _select_round_robin(qualified, rr_state)

            if not assigned:
                stats["skipped"] += 1
                stats["errors"].append(f"No manager for ticket {ticket.id}")
                continue

            # Create distribution record
            reason_parts = []
            if target_offices:
                reason_parts.append(f"Офис: {target_offices[0].name}")
            reason_parts.append(f"Тип: {nlp_result.type}")
            reason_parts.append(f"Язык: {nlp_result.language}")
            reason_parts.append(f"Сегмент: {ticket.segment}")

            dist = Distribution(
                id=uuid4(),
                ticket_id=ticket.id,
                ai_analysis_id=analysis.id,
                manager_id=assigned.id,
                reason=" | ".join(reason_parts),
            )
            db.add(dist)

            # Update manager load
            assigned.current_load += 1
            ticket.status = "distributed"
            stats["distributed"] += 1

        except Exception as e:
            stats["skipped"] += 1
            stats["errors"].append(f"Error for ticket {ticket.id}: {str(e)}")

    db.commit()
    return stats
