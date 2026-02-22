"""
Routing Engine for FIRE
Implements the cascade of business rules for ticket assignment.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Manager:
    """Manager data for routing decisions."""
    id: str
    full_name: str
    position: str
    skills: list[str]
    business_unit_id: Optional[str]
    business_unit_name: Optional[str]
    current_load: int


@dataclass
class TicketContext:
    """Context needed for routing a ticket."""
    segment: str  # Mass, VIP, Priority
    ticket_type: str
    language: str
    nearest_office: Optional[str]


class RoutingEngine:
    """
    Implements the cascade of business rules:
    1. Geographic filter → nearest office wins
    2. Skill filter:
       - VIP/Priority segment → manager must have "VIP" skill
       - Смена данных → manager must have position "Глав спец"
       - KZ language → manager must have "KZ" skill
       - ENG language → manager must have "ENG" skill
    3. Load balancing → pick 2 managers with lowest current workload
    4. Round Robin → assign tickets alternately between those 2
    """

    def __init__(self):
        # Round-robin state: tracks alternation between manager pairs
        self._rr_state: dict[tuple, int] = {}
        # 50/50 split counter for unknown locations
        self._office_counter = {"Астана": 0, "Алматы": 0}

    def reset_state(self):
        """Reset round-robin and split counters."""
        self._rr_state.clear()
        self._office_counter = {"Астана": 0, "Алматы": 0}

    def route_ticket(
        self,
        context: TicketContext,
        managers: list[Manager],
    ) -> tuple[Optional[Manager], str, list[str]]:
        """
        Route a ticket to the best available manager.

        Returns:
            (selected_manager, reason, rules_applied)
            manager is None if no suitable manager found
        """
        rules_applied = []

        if not managers:
            return None, "Нет доступных менеджеров", rules_applied

        # Step 1: Geographic filter
        filtered = self._apply_geographic_filter(context, managers)
        if filtered != managers:
            rules_applied.append(f"Географический фильтр: {context.nearest_office or 'разделение 50/50'}")

        # Step 2: Skill filter
        filtered, skill_rules = self._apply_skill_filter(context, filtered)
        rules_applied.extend(skill_rules)

        # If no managers after skill filter, try all managers without geographic filter
        if not filtered:
            logger.warning("No managers after filters, trying all managers with skill filter only")
            filtered, skill_rules = self._apply_skill_filter(context, managers)
            rules_applied.append("Fallback: все офисы")

        # If still no managers, try without skill filters
        if not filtered:
            logger.warning("No managers after skill filter, using all managers")
            filtered = managers
            rules_applied.append("Fallback: без фильтра навыков")

        # Step 3: Load balancing - get top 2 with lowest load
        sorted_by_load = sorted(filtered, key=lambda m: m.current_load)
        top_two = sorted_by_load[:2]
        rules_applied.append(f"Балансировка нагрузки: выбрано {len(top_two)} менеджеров с минимальной нагрузкой")

        # Step 4: Round Robin
        selected = self._apply_round_robin(top_two)
        rules_applied.append("Round-robin распределение")

        if selected:
            reason = self._build_reason(context, selected, rules_applied)
            return selected, reason, rules_applied

        return None, "Не удалось найти подходящего менеджера", rules_applied

    def _apply_geographic_filter(
        self,
        context: TicketContext,
        managers: list[Manager],
    ) -> list[Manager]:
        """Filter managers by geographic proximity to client."""

        # If we know the nearest office
        if context.nearest_office and context.nearest_office != "unknown":
            office_name = context.nearest_office.lower()
            filtered = [
                m for m in managers
                if m.business_unit_name and office_name in m.business_unit_name.lower()
            ]
            if filtered:
                return filtered

        # Unknown location - use 50/50 split between Astana and Almaty
        # Determine which office should get this ticket
        if self._office_counter["Астана"] <= self._office_counter["Алматы"]:
            target_office = "астана"
            self._office_counter["Астана"] += 1
        else:
            target_office = "алматы"
            self._office_counter["Алматы"] += 1

        filtered = [
            m for m in managers
            if m.business_unit_name and target_office in m.business_unit_name.lower()
        ]

        return filtered if filtered else managers

    def _apply_skill_filter(
        self,
        context: TicketContext,
        managers: list[Manager],
    ) -> tuple[list[Manager], list[str]]:
        """
        Filter managers by required skills/competencies.
        Returns (filtered_managers, rules_applied).
        """
        filtered = list(managers)
        rules = []

        # VIP/Priority segment requires VIP skill
        if context.segment in ("VIP", "Priority"):
            vip_managers = [m for m in filtered if "VIP" in m.skills]
            if vip_managers:
                filtered = vip_managers
                rules.append(f"Сегмент {context.segment}: требуется навык VIP")
            else:
                logger.warning(f"No VIP managers found for segment {context.segment}")

        # Смена данных requires Главный специалист position
        if context.ticket_type == "Смена данных":
            glav_spec = [m for m in filtered if "Главный специалист" in m.position]
            if glav_spec:
                filtered = glav_spec
                rules.append("Тип 'Смена данных': требуется должность 'Главный специалист'")
            else:
                logger.warning("No Главный специалист found for 'Смена данных' ticket")

        # KZ language requires KZ skill
        if context.language == "KZ":
            kz_managers = [m for m in filtered if "KZ" in m.skills]
            if kz_managers:
                filtered = kz_managers
                rules.append("Язык KZ: требуется навык KZ")
            else:
                logger.warning("No KZ-speaking managers found")

        # ENG language requires ENG skill
        if context.language == "ENG":
            eng_managers = [m for m in filtered if "ENG" in m.skills]
            if eng_managers:
                filtered = eng_managers
                rules.append("Язык ENG: требуется навык ENG")
            else:
                logger.warning("No English-speaking managers found")

        return filtered, rules

    def _apply_round_robin(self, managers: list[Manager]) -> Optional[Manager]:
        """
        Select one manager from the list using round-robin.
        Maintains state across calls for fair distribution.
        """
        if not managers:
            return None

        if len(managers) == 1:
            return managers[0]

        # Build a key for this pair of managers
        key = tuple(sorted(m.id for m in managers))

        if key not in self._rr_state:
            self._rr_state[key] = 0

        idx = self._rr_state[key] % len(managers)
        self._rr_state[key] += 1

        # Sort by ID to ensure consistent ordering
        sorted_managers = sorted(managers, key=lambda m: m.id)
        return sorted_managers[idx]

    def _build_reason(
        self,
        context: TicketContext,
        manager: Manager,
        rules_applied: list[str],
    ) -> str:
        """Build a human-readable reason string for the assignment."""
        parts = []

        if manager.business_unit_name:
            parts.append(f"Офис: {manager.business_unit_name}")

        parts.append(f"Тип: {context.ticket_type}")
        parts.append(f"Язык: {context.language}")
        parts.append(f"Сегмент: {context.segment}")
        parts.append(f"Нагрузка менеджера: {manager.current_load}")

        return " | ".join(parts)
