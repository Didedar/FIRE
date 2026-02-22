"""
RAG (Retrieval-Augmented Generation) module for FIRE.
Builds contextual knowledge from the database to enrich LLM prompts.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ManagerInfo:
    full_name: str
    position: str
    skills: list[str]
    office_name: str
    current_load: int


@dataclass
class OfficeInfo:
    name: str
    address: str
    latitude: float
    longitude: float
    manager_count: int


class RAGKnowledgeBase:
    """
    Builds context strings from operational data (managers, offices, rules)
    to inject into LLM prompts for better analysis and recommendations.
    """

    def __init__(self):
        self._managers: list[ManagerInfo] = []
        self._offices: list[OfficeInfo] = []

    def load_from_db(self, db_session) -> None:
        """Load managers and offices from SQLAlchemy session."""
        from app.models.manager import Manager
        from app.models.business_unit import BusinessUnit
        from sqlalchemy.orm import joinedload

        # Load offices
        offices = db_session.query(BusinessUnit).all()
        self._offices = [
            OfficeInfo(
                name=o.name,
                address=o.address or "",
                latitude=o.latitude or 0,
                longitude=o.longitude or 0,
                manager_count=len(o.managers) if hasattr(o, 'managers') and o.managers else 0,
            )
            for o in offices
        ]

        # Load managers with their offices
        managers = db_session.query(Manager).options(joinedload(Manager.business_unit)).all()
        self._managers = [
            ManagerInfo(
                full_name=m.full_name,
                position=m.position,
                skills=m.skills or [],
                office_name=m.business_unit.name if m.business_unit else "—",
                current_load=m.current_load,
            )
            for m in managers
        ]

        logger.info(f"RAG: загружено {len(self._offices)} офисов, {len(self._managers)} менеджеров")

    def load_direct(self, managers: list[ManagerInfo], offices: list[OfficeInfo]) -> None:
        """Load data directly (for testing or non-DB use)."""
        self._managers = managers
        self._offices = offices

    @property
    def is_loaded(self) -> bool:
        return len(self._managers) > 0 or len(self._offices) > 0

    def build_context(
        self,
        nearest_office: Optional[str] = None,
        segment: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        """
        Build a context string for the LLM prompt.
        Filters to the most relevant information based on known parameters.
        """
        if not self.is_loaded:
            return ""

        parts = []

        # Office information
        parts.append(self._build_offices_context())

        # Manager information (filtered by office if known)
        parts.append(self._build_managers_context(nearest_office, segment, language))

        # Business rules reference
        parts.append(self._build_rules_context())

        context = "\n".join(p for p in parts if p)

        # Limit context size (rough token estimation: ~4 chars per token)
        max_chars = 3000
        if len(context) > max_chars:
            context = context[:max_chars] + "\n... (данные сокращены)"

        return context

    def _build_offices_context(self) -> str:
        if not self._offices:
            return ""

        lines = ["[ОФИСЫ Freedom Finance — 15 городов Казахстана]"]
        for o in self._offices:
            lines.append(f"• {o.name} ({o.manager_count} менеджеров)")
        return "\n".join(lines)

    def _build_managers_context(
        self,
        nearest_office: Optional[str] = None,
        segment: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        if not self._managers:
            return ""

        # If we know the office, show managers from that office first
        if nearest_office:
            office_lower = nearest_office.lower()
            relevant = [m for m in self._managers if office_lower in m.office_name.lower()]
            others_count = len(self._managers) - len(relevant)

            if relevant:
                lines = [f"\n[МЕНЕДЖЕРЫ офиса {nearest_office}] ({len(relevant)} чел.)"]
                for m in sorted(relevant, key=lambda x: x.current_load):
                    skills_str = ", ".join(m.skills) if m.skills else "—"
                    lines.append(f"• {m.full_name} | {m.position} | Навыки: {skills_str} | Нагрузка: {m.current_load}")

                if others_count > 0:
                    lines.append(f"(+ ещё {others_count} менеджеров в других офисах)")
                return "\n".join(lines)

        # No office known — show summary by office
        from collections import defaultdict
        by_office = defaultdict(list)
        for m in self._managers:
            by_office[m.office_name].append(m)

        lines = [f"\n[МЕНЕДЖЕРЫ] (всего {len(self._managers)} чел.)"]
        for office_name, mgrs in sorted(by_office.items()):
            vip_count = sum(1 for m in mgrs if "VIP" in m.skills)
            kz_count = sum(1 for m in mgrs if "KZ" in m.skills)
            eng_count = sum(1 for m in mgrs if "ENG" in m.skills)
            skills_summary = []
            if vip_count:
                skills_summary.append(f"VIP:{vip_count}")
            if kz_count:
                skills_summary.append(f"KZ:{kz_count}")
            if eng_count:
                skills_summary.append(f"ENG:{eng_count}")
            skills_str = f" ({', '.join(skills_summary)})" if skills_summary else ""
            lines.append(f"• {office_name}: {len(mgrs)} менеджеров{skills_str}")

        return "\n".join(lines)

    def _build_rules_context(self) -> str:
        return """
[ПРАВИЛА МАРШРУТИЗАЦИИ]
• VIP/Priority сегмент → менеджер с навыком VIP
• Тип "Смена данных" → только Главный специалист
• Язык KZ → менеджер с навыком KZ
• Язык ENG → менеджер с навыком ENG
• Мошеннические действия → приоритет 9-10, немедленная обработка
• Жалобы → приоритет 4-6, отработка с клиентом
• Если офис не определён → распределение 50/50 между Астана и Алматы"""

    def get_managers_for_office(self, office_name: str) -> list[ManagerInfo]:
        """Get managers for a specific office."""
        office_lower = office_name.lower()
        return [m for m in self._managers if office_lower in m.office_name.lower()]

    def get_available_skills(self) -> set[str]:
        """Get all unique skills across managers."""
        skills = set()
        for m in self._managers:
            skills.update(m.skills)
        return skills
