"""
FIRE NLP Module
Provides NLP analysis, geocoding, and routing logic for customer tickets.
"""

from .analyzer import TicketAnalyzer
from .geocoding import GeocodingService
from .routing import RoutingEngine
from .schemas import AnalysisResult, GeoLocation

__all__ = [
    "TicketAnalyzer",
    "GeocodingService",
    "RoutingEngine",
    "AnalysisResult",
    "GeoLocation",
]
