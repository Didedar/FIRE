"""
Pydantic schemas for NLP module.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class GeoLocation(BaseModel):
    """Geographic coordinates."""
    latitude: float
    longitude: float
    city: Optional[str] = None
    source: Literal["nominatim", "dictionary", "fallback"] = "fallback"


class AnalysisResult(BaseModel):
    """Result of NLP analysis for a ticket."""
    ticket_type: Literal[
        "Жалоба",
        "Смена данных",
        "Консультация",
        "Претензия",
        "Неработоспособность приложения",
        "Мошеннические действия",
        "Спам",
    ]
    sentiment: Literal["Позитивный", "Нейтральный", "Негативный"]
    priority: int = Field(ge=1, le=10)
    language: Literal["KZ", "ENG", "RU"] = "RU"
    summary: str
    city: Optional[str] = None


class AnalysisRequest(BaseModel):
    """Request for ticket analysis."""
    text: str
    address: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Full response including NLP analysis and geocoding."""
    ticket_type: str
    sentiment: str
    priority: int
    language: str
    summary: str
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geo_source: Optional[str] = None
    nearest_office: Optional[str] = None
    processing_time_ms: Optional[float] = None


class RoutingResult(BaseModel):
    """Result of routing decision."""
    manager_id: str
    manager_name: str
    office: str
    reason: str
    rules_applied: list[str]
