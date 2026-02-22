"""
Distribution API — ticket processing, distribution, and stats
"""

import asyncio
import logging
import time
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.config import settings
from app.models.ticket import Ticket
from app.models.ai_analysis import AIAnalysis
from app.models.manager import Manager
from app.models.business_unit import BusinessUnit
from app.models.distribution import Distribution
from app.services.distribution import distribute_tickets
from app.services.nlp_client import analyze_ticket, load_rag_context
from app.services.csv_parser import (
    parse_tickets_csv,
    parse_managers_csv,
    parse_business_units_csv,
    save_uploaded_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["distribution"])


# ─────────────────────────────────────────────────────────────
# Request/Response Schemas
# ─────────────────────────────────────────────────────────────

class ProcessTicketRequest(BaseModel):
    """Request for processing a single ticket."""
    client_guid: str
    description: str
    segment: str = "Mass"  # Mass, VIP, Priority
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = None
    attachments: Optional[str] = None


class ProcessTicketResponse(BaseModel):
    """Response from ticket processing."""
    ticket_id: str
    status: str
    processing_time_ms: float
    analysis: dict
    assigned_manager: Optional[dict] = None
    routing_reason: Optional[str] = None


class BatchProcessResponse(BaseModel):
    """Response from batch processing."""
    total: int
    processed: int
    failed: int
    processing_time_ms: float
    errors: list[str]


class ProcessAllResponse(BaseModel):
    """Response from process-all endpoint."""
    business_units_loaded: int
    managers_loaded: int
    tickets_loaded: int
    tickets_processed: int
    tickets_failed: int
    total_time_ms: float
    errors: list[str]


# ─────────────────────────────────────────────────────────────
# Single Ticket Processing
# ─────────────────────────────────────────────────────────────

@router.post("/v1/process", response_model=ProcessTicketResponse)
async def process_single_ticket(
    request: ProcessTicketRequest,
    db: Session = Depends(get_db),
):
    """
    Process a single ticket: NLP analysis + geocoding + routing.
    Target: <10 seconds per ticket.
    """
    start_time = time.time()

    # Create ticket record
    ticket = Ticket(
        id=uuid4(),
        client_guid=request.client_guid,
        gender=request.gender,
        segment=request.segment,
        description=request.description,
        attachments=request.attachments,
        country=request.country,
        region=request.region,
        city=request.city,
        street=request.street,
        house=request.house,
        status="new",
    )

    if request.birth_date:
        try:
            from datetime import datetime
            ticket.birth_date = datetime.strptime(request.birth_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    db.add(ticket)
    db.flush()

    # Build address string for geocoding (city, region, country order per spec)
    address_parts = [
        request.city or "",
        request.region or "",
        request.country or "",
    ]
    address_str = ", ".join(p for p in address_parts if p)

    try:
        # Perform NLP analysis and geocoding (with RAG context)
        nlp_result = await analyze_ticket(
            text=request.description,
            address=address_str,
            country=request.country,
            db_session=db,
            segment=request.segment,
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

        # Update ticket with geo coords if available
        if nlp_result.latitude and nlp_result.longitude:
            ticket.latitude = nlp_result.latitude
            ticket.longitude = nlp_result.longitude
        ticket.status = "analyzed"

        # Perform routing
        assigned_manager, routing_reason = await _route_ticket(
            ticket=ticket,
            analysis=analysis,
            db=db,
        )

        if assigned_manager:
            dist = Distribution(
                id=uuid4(),
                ticket_id=ticket.id,
                ai_analysis_id=analysis.id,
                manager_id=assigned_manager.id,
                reason=routing_reason,
            )
            db.add(dist)
            assigned_manager.current_load += 1
            ticket.status = "distributed"

        db.commit()

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"Ticket {ticket.id} processed in {elapsed_ms:.0f}ms")

        return ProcessTicketResponse(
            ticket_id=str(ticket.id),
            status=ticket.status,
            processing_time_ms=round(elapsed_ms, 2),
            analysis={
                "type": nlp_result.type,
                "tonality": nlp_result.tonality,
                "priority": nlp_result.priority,
                "language": nlp_result.language,
                "summary": nlp_result.summary,
            },
            assigned_manager={
                "id": str(assigned_manager.id),
                "name": assigned_manager.full_name,
                "position": assigned_manager.position,
                "office": assigned_manager.business_unit.name if assigned_manager.business_unit else None,
            } if assigned_manager else None,
            routing_reason=routing_reason,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _route_ticket(
    ticket: Ticket,
    analysis: AIAnalysis,
    db: Session,
) -> tuple[Optional[Manager], str]:
    """Route a ticket to the best available manager."""
    from app.utils.geo import find_nearest_office

    offices = db.query(BusinessUnit).all()
    all_managers = db.query(Manager).options(joinedload(Manager.business_unit)).all()

    if not all_managers:
        return None, "Нет доступных менеджеров"

    # Geographic filter
    client_lat = analysis.geo_latitude or ticket.latitude
    client_lon = analysis.geo_longitude or ticket.longitude

    office_dicts = [
        {"id": o.id, "name": o.name, "latitude": o.latitude, "longitude": o.longitude}
        for o in offices
        if o.latitude is not None
    ]

    nearest = find_nearest_office(client_lat, client_lon, office_dicts)
    target_office_ids = set()

    if nearest:
        target_office_ids.add(nearest["id"])
    else:
        # Fallback: Astana and Almaty
        for o in offices:
            if "астана" in o.name.lower() or "алматы" in o.name.lower():
                target_office_ids.add(o.id)

    # Filter managers by office
    filtered = [m for m in all_managers if m.business_unit_id in target_office_ids]
    if not filtered:
        filtered = all_managers

    # Competency filter
    segment = ticket.segment
    ticket_type = analysis.type
    language = analysis.language

    # VIP/Priority segment
    if segment in ("VIP", "Priority"):
        vip_managers = [m for m in filtered if "VIP" in (m.skills or [])]
        if vip_managers:
            filtered = vip_managers

    # Смена данных → Главный специалист
    if ticket_type == "Смена данных":
        glav_spec = [m for m in filtered if "Главный специалист" in m.position]
        if glav_spec:
            filtered = glav_spec

    # Language skills
    if language == "KZ":
        kz_managers = [m for m in filtered if "KZ" in (m.skills or [])]
        if kz_managers:
            filtered = kz_managers
    elif language == "ENG":
        eng_managers = [m for m in filtered if "ENG" in (m.skills or [])]
        if eng_managers:
            filtered = eng_managers

    if not filtered:
        filtered = all_managers

    # Load balancing + Round Robin
    sorted_by_load = sorted(filtered, key=lambda m: m.current_load)
    selected = sorted_by_load[0] if sorted_by_load else None

    if selected:
        reason_parts = []
        if selected.business_unit:
            reason_parts.append(f"Офис: {selected.business_unit.name}")
        reason_parts.append(f"Тип: {ticket_type}")
        reason_parts.append(f"Язык: {language}")
        reason_parts.append(f"Сегмент: {segment}")
        reason = " | ".join(reason_parts)
        return selected, reason

    return None, "Не удалось найти подходящего менеджера"


# ─────────────────────────────────────────────────────────────
# Batch Processing
# ─────────────────────────────────────────────────────────────

@router.post("/v1/batch", response_model=BatchProcessResponse)
async def process_batch(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Process a batch of tickets from CSV file.
    Uses asyncio.gather + Semaphore(10) for parallel processing.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    start_time = time.time()

    # Save and parse CSV
    content = await file.read()
    path = save_uploaded_file(content, f"batch_{file.filename}")

    try:
        count = parse_tickets_csv(path, db)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV parse error: {str(e)}")

    # Get all new tickets
    tickets = db.query(Ticket).filter(Ticket.status == "new").all()

    # Load RAG context once for the whole batch
    load_rag_context(db)

    processed = 0
    failed = 0
    errors = []

    semaphore = asyncio.Semaphore(settings.BATCH_SEMAPHORE_LIMIT)

    async def process_one_batch(ticket: Ticket) -> bool:
        """Process a single ticket with semaphore."""
        async with semaphore:
            try:
                # Build address per spec: city, region, country
                address_parts = [
                    ticket.city or "",
                    ticket.region or "",
                    ticket.country or "",
                ]
                address_str = ", ".join(p for p in address_parts if p)

                nlp_result = await analyze_ticket(
                    text=ticket.description or "",
                    address=address_str,
                    country=ticket.country,
                    db_session=db,
                    segment=ticket.segment,
                )

                # Save analysis
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

                if nlp_result.latitude and nlp_result.longitude:
                    ticket.latitude = nlp_result.latitude
                    ticket.longitude = nlp_result.longitude
                ticket.status = "analyzed"

                # Route ticket
                manager, reason = await _route_ticket(ticket, analysis, db)

                if manager:
                    dist = Distribution(
                        id=uuid4(),
                        ticket_id=ticket.id,
                        ai_analysis_id=analysis.id,
                        manager_id=manager.id,
                        reason=reason,
                    )
                    db.add(dist)
                    manager.current_load += 1
                    ticket.status = "distributed"

                return True

            except Exception as e:
                logger.error(f"Error processing ticket {ticket.id}: {e}")
                errors.append(f"Ticket {ticket.id}: {str(e)}")
                return False

    # Process all tickets in parallel with semaphore
    results = await asyncio.gather(
        *[process_one_batch(t) for t in tickets],
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, Exception):
            failed += 1
            errors.append(str(result))
        elif result:
            processed += 1
        else:
            failed += 1

    db.commit()

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"Batch processed: {processed}/{len(tickets)} in {elapsed_ms:.0f}ms")

    return BatchProcessResponse(
        total=len(tickets),
        processed=processed,
        failed=failed,
        processing_time_ms=round(elapsed_ms, 2),
        errors=errors[:10],  # Limit errors in response
    )


# ─────────────────────────────────────────────────────────────
# Process All (load CSVs + process all 200 tickets)
# ─────────────────────────────────────────────────────────────

@router.post("/v1/process-all", response_model=ProcessAllResponse)
async def process_all(db: Session = Depends(get_db)):
    """
    Load all 3 CSV files from project root and process all 200 tickets.
    Order: business_units.csv → managers.csv → tickets.csv → AI analysis → routing
    """
    import os
    start_time = time.time()
    errors = []

    # Find project root (where CSV files are located)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    bu_path = os.path.join(project_root, "business_units.csv")
    managers_path = os.path.join(project_root, "managers.csv")
    tickets_path = os.path.join(project_root, "tickets.csv")

    # Check files exist
    for path, name in [(bu_path, "business_units.csv"), (managers_path, "managers.csv"), (tickets_path, "tickets.csv")]:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"CSV file not found: {name} at {path}")

    # Step 1: Load business units first
    try:
        bu_count = parse_business_units_csv(bu_path, db)
        logger.info(f"Loaded {bu_count} business units")
    except Exception as e:
        logger.error(f"Failed to load business units: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load business units: {str(e)}")

    # Step 2: Load managers
    try:
        mgr_count = parse_managers_csv(managers_path, db)
        logger.info(f"Loaded {mgr_count} managers")
    except Exception as e:
        logger.error(f"Failed to load managers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load managers: {str(e)}")

    # Step 3: Load tickets
    try:
        tkt_count = parse_tickets_csv(tickets_path, db)
        logger.info(f"Loaded {tkt_count} tickets")
    except Exception as e:
        logger.error(f"Failed to load tickets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load tickets: {str(e)}")

    # Step 4: Process all tickets
    tickets = db.query(Ticket).filter(Ticket.status == "new").all()
    processed = 0
    failed = 0

    # Load RAG context once for the whole batch
    load_rag_context(db)

    semaphore = asyncio.Semaphore(settings.BATCH_SEMAPHORE_LIMIT)

    async def process_one(ticket: Ticket) -> bool:
        """Process a single ticket with semaphore."""
        async with semaphore:
            try:
                address_parts = [
                    ticket.city or "",
                    ticket.region or "",
                    ticket.country or "",
                ]
                address_str = ", ".join(p for p in address_parts if p)

                nlp_result = await analyze_ticket(
                    text=ticket.description or "",
                    address=address_str,
                    country=ticket.country,
                    db_session=db,
                    segment=ticket.segment,
                )

                # Save analysis
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

                if nlp_result.latitude and nlp_result.longitude:
                    ticket.latitude = nlp_result.latitude
                    ticket.longitude = nlp_result.longitude
                ticket.status = "analyzed"

                # Route ticket
                manager, reason = await _route_ticket(ticket, analysis, db)

                if manager:
                    dist = Distribution(
                        id=uuid4(),
                        ticket_id=ticket.id,
                        ai_analysis_id=analysis.id,
                        manager_id=manager.id,
                        reason=reason,
                    )
                    db.add(dist)
                    manager.current_load += 1
                    ticket.status = "distributed"

                return True

            except Exception as e:
                logger.error(f"Error processing ticket {ticket.id}: {e}")
                errors.append(f"Ticket {ticket.id}: {str(e)}")
                return False

    # Process all tickets in parallel with semaphore
    results = await asyncio.gather(
        *[process_one(t) for t in tickets],
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, Exception):
            failed += 1
            errors.append(str(result))
        elif result:
            processed += 1
        else:
            failed += 1

    db.commit()

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"Process-all completed: {processed}/{len(tickets)} in {elapsed_ms:.0f}ms")

    return ProcessAllResponse(
        business_units_loaded=bu_count,
        managers_loaded=mgr_count,
        tickets_loaded=tkt_count,
        tickets_processed=processed,
        tickets_failed=failed,
        total_time_ms=round(elapsed_ms, 2),
        errors=errors[:20],
    )


# ─────────────────────────────────────────────────────────────
# Distribute All (legacy endpoint)
# ─────────────────────────────────────────────────────────────

@router.post("/distribute")
async def trigger_distribution(db: Session = Depends(get_db)):
    """Trigger the distribution pipeline for all unassigned tickets."""
    result = await distribute_tickets(db)
    return result


# ─────────────────────────────────────────────────────────────
# Statistics
# ─────────────────────────────────────────────────────────────

@router.get("/v1/stats")
@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Dashboard statistics."""
    total_tickets = db.query(Ticket).count()
    distributed = db.query(Ticket).filter(Ticket.status == "distributed").count()
    analyzed = db.query(Ticket).filter(Ticket.status == "analyzed").count()
    pending = db.query(Ticket).filter(Ticket.status == "new").count()

    # Average priority
    avg_p = db.query(func.avg(AIAnalysis.priority)).scalar()
    avg_priority = round(float(avg_p), 1) if avg_p else 0

    # Type distribution
    type_rows = (
        db.query(AIAnalysis.type, func.count(AIAnalysis.id))
        .group_by(AIAnalysis.type)
        .all()
    )
    type_distribution = {row[0]: row[1] for row in type_rows}

    # Tonality distribution
    ton_rows = (
        db.query(AIAnalysis.tonality, func.count(AIAnalysis.id))
        .group_by(AIAnalysis.tonality)
        .all()
    )
    tonality_distribution = {row[0]: row[1] for row in ton_rows}

    # Language distribution
    lang_rows = (
        db.query(AIAnalysis.language, func.count(AIAnalysis.id))
        .group_by(AIAnalysis.language)
        .all()
    )
    language_distribution = {row[0]: row[1] for row in lang_rows}

    # Manager load
    managers = db.query(Manager).options(joinedload(Manager.business_unit)).all()
    manager_load = [
        {
            "name": m.full_name,
            "load": m.current_load,
            "position": m.position,
            "office": m.business_unit.name if m.business_unit else "—",
        }
        for m in managers
    ]
    manager_load.sort(key=lambda x: x["load"], reverse=True)

    # Office distribution
    office_rows = (
        db.query(BusinessUnit.name, func.count(Distribution.id))
        .join(Manager, Manager.business_unit_id == BusinessUnit.id)
        .join(Distribution, Distribution.manager_id == Manager.id)
        .group_by(BusinessUnit.name)
        .all()
    )
    office_distribution = {row[0]: row[1] for row in office_rows}

    return {
        "total_tickets": total_tickets,
        "distributed_tickets": distributed,
        "analyzed_tickets": analyzed,
        "pending_tickets": pending,
        "avg_priority": avg_priority,
        "type_distribution": type_distribution,
        "tonality_distribution": tonality_distribution,
        "language_distribution": language_distribution,
        "manager_load": manager_load,
        "office_distribution": office_distribution,
    }


# ─────────────────────────────────────────────────────────────
# AI Assistant
# ─────────────────────────────────────────────────────────────

@router.post("/ai-assistant")
async def ai_assistant(request: dict, db: Session = Depends(get_db)):
    """
    AI assistant that takes natural language queries about distributions.
    Uses RAG context + Groq LLM for intelligent answers, with keyword fallback.
    Returns structured data for chart rendering.
    """
    query = request.get("query", "").lower()

    # ── Keyword-based structured queries (for charts) ──
    if "тип" in query and ("город" in query or "офис" in query):
        rows = (
            db.query(Ticket.city, AIAnalysis.type, func.count(Ticket.id))
            .join(AIAnalysis, AIAnalysis.ticket_id == Ticket.id)
            .group_by(Ticket.city, AIAnalysis.type)
            .all()
        )
        data = {}
        for city, t_type, cnt in rows:
            city_name = city or "Неизвестно"
            if city_name not in data:
                data[city_name] = {}
            data[city_name][t_type] = cnt

        return {
            "answer": "Распределение типов обращений по городам:",
            "chart_type": "grouped_bar",
            "data": data,
        }

    elif "нагрузк" in query or ("менеджер" in query and ("список" in query or "все" in query or "покаж" in query)):
        managers = db.query(Manager).options(joinedload(Manager.business_unit)).all()
        data = [
            {"name": m.full_name, "load": m.current_load, "office": m.business_unit.name if m.business_unit else "—",
             "position": m.position, "skills": m.skills or []}
            for m in managers
        ]
        return {
            "answer": "Нагрузка менеджеров:",
            "chart_type": "bar",
            "data": sorted(data, key=lambda x: x["load"], reverse=True),
        }

    elif "тональност" in query or "сентимент" in query:
        rows = (
            db.query(AIAnalysis.tonality, func.count(AIAnalysis.id))
            .group_by(AIAnalysis.tonality)
            .all()
        )
        return {
            "answer": "Распределение тональности обращений:",
            "chart_type": "pie",
            "data": {row[0]: row[1] for row in rows},
        }

    elif "приоритет" in query:
        rows = (
            db.query(AIAnalysis.priority, func.count(AIAnalysis.id))
            .group_by(AIAnalysis.priority)
            .order_by(AIAnalysis.priority)
            .all()
        )
        return {
            "answer": "Распределение по приоритету:",
            "chart_type": "bar",
            "data": [{"priority": row[0], "count": row[1]} for row in rows],
        }

    elif "язык" in query or "language" in query:
        rows = (
            db.query(AIAnalysis.language, func.count(AIAnalysis.id))
            .group_by(AIAnalysis.language)
            .all()
        )
        return {
            "answer": "Распределение по языкам:",
            "chart_type": "pie",
            "data": {row[0]: row[1] for row in rows},
        }

    elif "сегмент" in query:
        rows = (
            db.query(Ticket.segment, func.count(Ticket.id))
            .group_by(Ticket.segment)
            .all()
        )
        return {
            "answer": "Распределение по сегментам:",
            "chart_type": "pie",
            "data": {row[0]: row[1] for row in rows},
        }

    else:
        # ── RAG-powered LLM answer for free-form questions ──
        answer = await _rag_answer(request.get("query", ""), db)
        return {
            "answer": answer,
            "chart_type": None,
            "data": None,
        }


async def _rag_answer(query: str, db: Session) -> str:
    """
    Use RAG context + Groq LLM to answer free-form questions about the system.
    Falls back to basic stats if LLM is unavailable.
    """
    from app.config import settings

    # Build RAG context from DB
    rag = load_rag_context(db)
    from app.services.nlp_client import _get_rag
    rag_kb = _get_rag()

    # Gather live stats
    total = db.query(Ticket).count()
    distributed = db.query(Ticket).filter(Ticket.status == "distributed").count()
    analyzed = db.query(Ticket).filter(Ticket.status == "analyzed").count()
    pending = db.query(Ticket).filter(Ticket.status == "new").count()

    stats_context = (
        f"\n[ТЕКУЩАЯ СТАТИСТИКА]\n"
        f"Всего обращений: {total}\n"
        f"Распределено: {distributed}\n"
        f"Проанализировано (без менеджера): {analyzed}\n"
        f"Ожидают обработки: {pending}\n"
    )

    # Build full context
    rag_context = ""
    if rag_kb.is_loaded:
        rag_context = rag_kb.build_context()
    rag_context += stats_context

    # Try LLM
    if settings.GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты — ИИ-ассистент системы FIRE (Freedom Intelligent Routing Engine) "
                            "для банка Freedom Finance. Отвечай на вопросы по данным системы. "
                            "Отвечай кратко и по делу на русском языке.\n\n"
                            f"--- КОНТЕКСТ ---\n{rag_context}"
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.warning(f"AI assistant LLM error: {e}")

    # Fallback
    return (
        f"Всего обращений: {total}, распределено: {distributed}, "
        f"ожидают: {pending}. "
        f"Попробуйте запросить: 'типы обращений по городам', "
        f"'нагрузка менеджеров', 'тональность', 'приоритет', 'язык', 'сегмент'."
    )
