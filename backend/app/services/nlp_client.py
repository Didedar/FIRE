"""
NLP Client Service
Integrates with the NLP module for ticket analysis and geocoding.
"""

import sys
import os
import logging
from typing import Optional

# Add nlp_module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from nlp_module.analyzer import TicketAnalyzer
from nlp_module.geocoding import GeocodingService, GeoLocation
from nlp_module.schemas import AnalysisResult

from app.config import settings
from app.schemas import NLPResponse

logger = logging.getLogger(__name__)

# Initialize services (lazy loaded)
_analyzer: Optional[TicketAnalyzer] = None
_geocoder: Optional[GeocodingService] = None


def _get_analyzer() -> TicketAnalyzer:
    """Get or create the ticket analyzer."""
    global _analyzer
    if _analyzer is None:
        api_key = settings.GROQ_API_KEY
        if not api_key:
            logger.warning("GROQ_API_KEY not set, analyzer will use fallback mode")
            # Create a dummy analyzer that uses fallback
            _analyzer = _DummyAnalyzer()
        else:
            _analyzer = TicketAnalyzer(api_key=api_key)
    return _analyzer


def _get_geocoder() -> GeocodingService:
    """Get or create the geocoding service."""
    global _geocoder
    if _geocoder is None:
        _geocoder = GeocodingService(timeout=5.0)
    return _geocoder


class _DummyAnalyzer:
    """Fallback analyzer when GROQ_API_KEY is not available."""

    async def analyze(self, text: str) -> AnalysisResult:
        return self.analyze_sync(text)

    def analyze_sync(self, text: str) -> AnalysisResult:
        """Generate fallback analysis."""
        ticket_type = self._guess_type(text)
        sentiment = self._guess_sentiment(text)
        language = self._guess_language(text)
        priority = self._guess_priority(ticket_type)

        summary = f"Обращение типа '{ticket_type}'. "
        if sentiment == "Негативный":
            summary += "Клиент выражает недовольство. Рекомендация: связаться в приоритетном порядке."
        elif sentiment == "Позитивный":
            summary += "Клиент настроен позитивно. Рекомендация: стандартная обработка."
        else:
            summary += "Рекомендация: обработка по стандартному регламенту."

        return AnalysisResult(
            ticket_type=ticket_type,
            sentiment=sentiment,
            priority=priority,
            language=language,
            summary=summary,
            city=None,
        )

    def _guess_language(self, text: str) -> str:
        if not text:
            return "RU"
        kz_chars = set("ӘәҒғҚқҢңӨөҰұҮүІіҺһ")
        if any(c in kz_chars for c in text):
            return "KZ"
        latin_count = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        alpha_count = sum(1 for c in text if c.isalpha())
        if alpha_count > 0 and latin_count / alpha_count > 0.7:
            return "ENG"
        return "RU"

    def _guess_type(self, text: str) -> str:
        if not text:
            return "Консультация"
        tl = text.lower()
        if any(w in tl for w in ["мошенни", "fraud", "украли", "списали"]):
            return "Мошеннические действия"
        if any(w in tl for w in ["не работает", "ошибка", "сбой", "приложение"]):
            return "Неработоспособность приложения"
        if any(w in tl for w in ["претензи", "возврат", "компенсац"]):
            return "Претензия"
        if any(w in tl for w in ["жалоба", "недоволен", "ужасн", "плох"]):
            return "Жалоба"
        if any(w in tl for w in ["сменить", "изменить", "обновить", "данные"]):
            return "Смена данных"
        if any(w in tl for w in ["спам", "реклама", "spam"]):
            return "Спам"
        if any(w in tl for w in ["вопрос", "подскажите", "консультац", "как"]):
            return "Консультация"
        return "Консультация"

    def _guess_sentiment(self, text: str) -> str:
        if not text:
            return "Нейтральный"
        tl = text.lower()
        neg = sum(1 for w in ["плох", "ужас", "зл", "недовол", "отврат", "жалоб", "хам"] if w in tl)
        pos = sum(1 for w in ["спасибо", "отлично", "хорош", "супер", "доволен", "рад"] if w in tl)
        if neg > pos:
            return "Негативный"
        if pos > neg:
            return "Позитивный"
        return "Нейтральный"

    def _guess_priority(self, ticket_type: str) -> int:
        priority_map = {
            "Мошеннические действия": 9,
            "Неработоспособность приложения": 7,
            "Претензия": 7,
            "Жалоба": 5,
            "Смена данных": 4,
            "Консультация": 3,
            "Спам": 1,
        }
        return priority_map.get(ticket_type, 5)


async def analyze_ticket(text: str, address: str, country: str = None) -> NLPResponse:
    """
    Analyze ticket text and geocode address.
    Returns combined NLP + geo response with nearest office.
    """
    analyzer = _get_analyzer()
    geocoder = _get_geocoder()

    logger.info("=" * 60)
    logger.info("🔥 NLP Pipeline START")
    logger.info(f"📝 Текст ({len(text)} символов): {text[:120]}...")
    logger.info(f"📍 Адрес: {address or '—'}")

    # ── Step 1: NLP Analysis ──────────────────────
    logger.info("─" * 40)
    logger.info("🧠 [1/3] Анализ текста в NLP модуле...")
    try:
        analysis = await analyzer.analyze(text)
        logger.info(f"   ✅ Тип: {analysis.ticket_type}")
        logger.info(f"   ✅ Тональность: {analysis.sentiment}")
        logger.info(f"   ✅ Приоритет: {analysis.priority}/10")
        logger.info(f"   ✅ Язык: {analysis.language}")
        logger.info(f"   ✅ Summary: {(analysis.summary or '')[:80]}...")
    except Exception as e:
        logger.error(f"   ❌ NLP-анализ упал: {e}")
        logger.info("   ⚠️  Используем fallback-анализатор")
        analysis = _DummyAnalyzer().analyze_sync(text)
        logger.info(f"   📌 Fallback тип: {analysis.ticket_type}")

    # ── Step 2: Geocoding ─────────────────────────
    logger.info("─" * 40)
    logger.info("🌍 [2/3] Определение гео-позиции...")
    lat, lon = None, None
    geo_city = None
    location = None

    try:
        if address:
            logger.info(f"   🔍 Геокодинг адреса: '{address}'")
            location = await geocoder.geocode(address)
            if location:
                lat = location.latitude
                lon = location.longitude
                geo_city = location.city
                logger.info(f"   ✅ Найдено: {geo_city} ({lat:.4f}, {lon:.4f})")
            else:
                logger.info("   ⚠️  Адрес не найден через геокодер")

        if lat is None and analysis.city:
            logger.info(f"   🔍 Пробуем город из NLP: '{analysis.city}'")
            location = await geocoder.geocode(analysis.city)
            if location:
                lat = location.latitude
                lon = location.longitude
                geo_city = location.city
                logger.info(f"   ✅ Найдено: {geo_city} ({lat:.4f}, {lon:.4f})")

        if lat is None:
            extracted_city = geocoder.extract_city_from_text(text)
            if extracted_city:
                logger.info(f"   🔍 Извлечён город из текста: '{extracted_city}'")
                location = geocoder._geocode_dictionary(extracted_city)
                if location:
                    lat = location.latitude
                    lon = location.longitude
                    geo_city = location.city
                    logger.info(f"   ✅ Найдено по словарю: {geo_city} ({lat:.4f}, {lon:.4f})")

        if lat is None:
            logger.info("   ⚠️  Гео-позиция не определена")

    except Exception as e:
        logger.error(f"   ❌ Геокодинг упал: {e}")

    # ── Step 3: Nearest Office ────────────────────
    logger.info("─" * 40)
    logger.info("🏢 [3/3] Поиск ближайшего офиса...")
    nearest_office = None
    if location:
        office_name, _ = geocoder.determine_nearest_office(location, country)
        if office_name != "unknown":
            nearest_office = office_name
            logger.info(f"   ✅ Ближайший офис: {nearest_office}")
        else:
            logger.info("   ⚠️  Офис не определён")
    else:
        logger.info("   ⏭️  Пропущено (нет координат)")

    logger.info("=" * 60)
    logger.info(f"🔥 NLP Pipeline DONE → Тип: {analysis.ticket_type} | "
                f"Тон: {analysis.sentiment} | Приоритет: {analysis.priority} | "
                f"Офис: {nearest_office or '—'}")
    logger.info("=" * 60)

    return NLPResponse(
        type=analysis.ticket_type,
        tonality=analysis.sentiment,
        priority=analysis.priority,
        language=analysis.language,
        summary=analysis.summary,
        latitude=lat,
        longitude=lon,
        nearest_office=nearest_office,
    )


async def close_services():
    """Close all service connections."""
    global _geocoder
    if _geocoder:
        await _geocoder.close()
