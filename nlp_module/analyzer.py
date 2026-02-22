"""
Ticket Analyzer using Groq LLM
"""

import os
import json
import logging
import time
from typing import Optional

from groq import Groq, APIError, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .schemas import AnalysisResult

logger = logging.getLogger(__name__)

# System prompt for LLM (exact from spec)
SYSTEM_PROMPT_BASE = """Ты — классификатор обращений клиентов банка Freedom Finance.
Проанализируй текст и верни ТОЛЬКО валидный JSON без markdown:
{
"ticket_type": "<Жалоба|Смена данных|Консультация|Претензия|Неработоспособность приложения|Мошеннические действия|Спам>",
"sentiment": "<Позитивный|Нейтральный|Негативный>",
"priority": <1-10>,
"language": "<KZ|ENG|RU>",
"summary": "<суть 1-2 предложения на русском>. Рекомендация: <действие для менеджера>"
}
Приоритет: Мошеннические действия=9-10, Претензии с финансовыми потерями=7-8, Жалобы=4-6, Консультации/Спам=1-3.
Язык по умолчанию RU. Резюме всегда на русском."""

# Legacy alias for backward compatibility
SYSTEM_PROMPT = SYSTEM_PROMPT_BASE

# Valid values for validation
VALID_TICKET_TYPES = {
    "Жалоба",
    "Смена данных",
    "Консультация",
    "Претензия",
    "Неработоспособность приложения",
    "Мошеннические действия",
    "Спам",
}

VALID_SENTIMENTS = {"Позитивный", "Нейтральный", "Негативный"}
VALID_LANGUAGES = {"KZ", "ENG", "RU"}


class TicketAnalyzer:
    """Analyzes customer tickets using Groq LLM."""

    MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")

        self.client = Groq(api_key=self.api_key)
        logger.info("TicketAnalyzer initialized with Groq client")

    def _build_prompt(self, rag_context: Optional[str] = None) -> str:
        """Build system prompt, optionally enriched with RAG context."""
        if rag_context:
            return f"{SYSTEM_PROMPT_BASE}\n\n--- КОНТЕКСТ КОМПАНИИ (используй для рекомендаций) ---\n{rag_context}"
        return SYSTEM_PROMPT_BASE

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=lambda retry_state: logger.warning(
            f"Rate limited, retrying in {retry_state.next_action.sleep} seconds..."
        ),
    )
    async def analyze(self, text: str, rag_context: Optional[str] = None) -> AnalysisResult:
        """
        Analyze ticket text using Groq LLM.
        Optionally accepts RAG context to enrich the prompt with company data.
        Returns structured analysis result.
        """
        if not text or not text.strip():
            return self._fallback_analysis("")

        start_time = time.time()
        system_prompt = self._build_prompt(rag_context)

        try:
            logger.info("=" * 50)
            logger.info(f"🤖 Groq LLM: Отправляю запрос → модель {self.MODEL}")
            logger.info(f"📝 Текст для анализа ({len(text)} символов): {text[:100]}...")
            if rag_context:
                logger.info(f"📚 RAG контекст: {len(rag_context)} символов")

            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=500,
            )

            elapsed = (time.time() - start_time) * 1000
            logger.info(f"⚡ Groq LLM: Ответ получен за {elapsed:.0f}мс")

            content = response.choices[0].message.content
            logger.info(f"📦 Groq LLM raw JSON: {content}")

            result = self._parse_response(content, text)
            logger.info(f"✅ Результат NLP анализа:")
            logger.info(f"   Тип:         {result.ticket_type}")
            logger.info(f"   Тональность: {result.sentiment}")
            logger.info(f"   Приоритет:   {result.priority}/10")
            logger.info(f"   Язык:        {result.language}")
            logger.info(f"   Summary:     {(result.summary or '')[:80]}...")
            logger.info("=" * 50)
            return result

        except RateLimitError:
            logger.error("❌ Groq: Rate limit exceeded")
            raise
        except APIError as e:
            logger.error(f"❌ Groq API error: {e}")
            return self._fallback_analysis(text)
        except Exception as e:
            logger.error(f"❌ Unexpected error during analysis: {e}")
            return self._fallback_analysis(text)

    def analyze_sync(self, text: str, rag_context: Optional[str] = None) -> AnalysisResult:
        """Synchronous version of analyze for non-async contexts."""
        if not text or not text.strip():
            return self._fallback_analysis("")

        start_time = time.time()
        system_prompt = self._build_prompt(rag_context)

        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=500,
            )

            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Groq analysis completed in {elapsed:.0f}ms")

            content = response.choices[0].message.content
            return self._parse_response(content, text)

        except RateLimitError:
            logger.error("Groq rate limit exceeded")
            raise
        except APIError as e:
            logger.error(f"Groq API error: {e}")
            return self._fallback_analysis(text)
        except Exception as e:
            logger.error(f"Unexpected error during analysis: {e}")
            return self._fallback_analysis(text)

    def _parse_response(self, content: str, original_text: str) -> AnalysisResult:
        """Parse and validate LLM JSON response."""
        try:
            data = json.loads(content)

            # Validate and normalize ticket_type
            ticket_type = data.get("ticket_type", "Консультация")
            if ticket_type not in VALID_TICKET_TYPES:
                ticket_type = self._guess_type(original_text)

            # Validate and normalize sentiment
            sentiment = data.get("sentiment", "Нейтральный")
            if sentiment not in VALID_SENTIMENTS:
                sentiment = "Нейтральный"

            # Validate priority
            priority = data.get("priority", 5)
            if not isinstance(priority, int):
                try:
                    priority = int(priority)
                except (ValueError, TypeError):
                    priority = 5
            priority = max(1, min(10, priority))

            # Validate language
            language = data.get("language", "RU")
            if language not in VALID_LANGUAGES:
                language = self._guess_language(original_text)

            # Get summary
            summary = data.get("summary", "")
            if not summary:
                summary = f"Обращение типа '{ticket_type}'. Требуется стандартная обработка."

            # Get city (optional, may not be returned by LLM)
            city = data.get("city")
            if city in ("null", "", None):
                city = None

            return AnalysisResult(
                ticket_type=ticket_type,
                sentiment=sentiment,
                priority=priority,
                language=language,
                summary=summary,
                city=city,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return self._fallback_analysis(original_text)

    def _fallback_analysis(self, text: str) -> AnalysisResult:
        """Generate fallback analysis when LLM fails."""
        logger.warning("Using fallback analysis")

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
        """Simple heuristic to detect language."""
        if not text:
            return "RU"

        # Kazakh-specific characters
        kz_chars = set("ӘәҒғҚқҢңӨөҰұҮүІіҺһ")
        if any(c in kz_chars for c in text):
            return "KZ"

        # Check for mostly Latin chars
        latin_count = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        alpha_count = sum(1 for c in text if c.isalpha())
        if alpha_count > 0 and latin_count / alpha_count > 0.7:
            return "ENG"

        return "RU"

    def _guess_type(self, text: str) -> str:
        """Keyword-based classification fallback."""
        if not text:
            return "Консультация"

        tl = text.lower()

        if any(w in tl for w in ["мошенни", "fraud", "украли", "списали без согласия", "взлом"]):
            return "Мошеннические действия"
        if any(w in tl for w in ["не работает", "ошибка", "сбой", "приложение", "crash", "не открывается"]):
            return "Неработоспособность приложения"
        if any(w in tl for w in ["претензи", "возврат", "компенсац", "требую вернуть"]):
            return "Претензия"
        if any(w in tl for w in ["жалоба", "недоволен", "ужасн", "плох", "хам"]):
            return "Жалоба"
        if any(w in tl for w in ["сменить", "изменить", "обновить данные", "новый адрес", "смена номера"]):
            return "Смена данных"
        if any(w in tl for w in ["спам", "реклама", "spam", "рассылка"]):
            return "Спам"
        if any(w in tl for w in ["вопрос", "подскажите", "консультац", "как", "интересует"]):
            return "Консультация"

        return "Консультация"

    def _guess_sentiment(self, text: str) -> str:
        """Simple sentiment heuristic."""
        if not text:
            return "Нейтральный"

        tl = text.lower()

        neg_words = ["плох", "ужас", "зл", "недовол", "отврат", "жалоб", "хам", "безобраз", "кошмар"]
        pos_words = ["спасибо", "отлично", "хорош", "супер", "доволен", "рад", "благодар"]

        neg = sum(1 for w in neg_words if w in tl)
        pos = sum(1 for w in pos_words if w in tl)

        if neg > pos:
            return "Негативный"
        if pos > neg:
            return "Позитивный"
        return "Нейтральный"

    def _guess_priority(self, ticket_type: str) -> int:
        """Estimate priority based on ticket type."""
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
