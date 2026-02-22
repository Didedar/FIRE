"""
Geocoding Service for FIRE
Uses cascade: Nominatim OSM API → Kazakhstan city dictionary fallback
"""

import math
import logging
from typing import Optional, Tuple
import httpx

from .schemas import GeoLocation

logger = logging.getLogger(__name__)

# All 15 Office coordinates (exact from spec)
OFFICE_COORDINATES: dict[str, Tuple[float, float]] = {
    "Актау": (43.6355, 51.1680),
    "Актобе": (50.2839, 57.1670),
    "Алматы": (43.2380, 76.9458),
    "Астана": (51.1694, 71.4491),
    "Атырау": (47.1068, 51.9032),
    "Караганда": (49.8047, 73.1094),
    "Кокшетау": (53.2836, 69.3783),
    "Костанай": (53.2144, 63.6246),
    "Кызылорда": (44.8488, 65.5093),
    "Павлодар": (52.2873, 76.9674),
    "Петропавловск": (54.8720, 69.1414),
    "Тараз": (42.9000, 71.3667),
    "Уральск": (51.2333, 51.3667),
    "Усть-Каменогорск": (49.9482, 82.6279),
    "Шымкент": (42.3154, 69.5967),
}

# Comprehensive Kazakhstan city dictionary with multiple spellings (RU/KZ/EN)
KAZAKHSTAN_CITIES: dict[str, Tuple[float, float]] = {
    # Astana / Nur-Sultan
    "астана": (51.1694, 71.4491),
    "нур-султан": (51.1694, 71.4491),
    "astana": (51.1694, 71.4491),
    "nur-sultan": (51.1694, 71.4491),
    "nursultan": (51.1694, 71.4491),
    "астана қ": (51.1694, 71.4491),
    # Almaty
    "алматы": (43.2220, 76.8512),
    "алма-ата": (43.2220, 76.8512),
    "almaty": (43.2220, 76.8512),
    "alma-ata": (43.2220, 76.8512),
    "алматы қ": (43.2220, 76.8512),
    # Shymkent
    "шымкент": (42.3417, 69.5901),
    "чимкент": (42.3417, 69.5901),
    "shymkent": (42.3417, 69.5901),
    "chimkent": (42.3417, 69.5901),
    # Karaganda
    "караганда": (49.8047, 73.1094),
    "караганды": (49.8047, 73.1094),
    "karaganda": (49.8047, 73.1094),
    "qaraghandy": (49.8047, 73.1094),
    # Aktobe
    "актобе": (50.2839, 57.1670),
    "актюбинск": (50.2839, 57.1670),
    "aktobe": (50.2839, 57.1670),
    "aqtobe": (50.2839, 57.1670),
    # Taraz
    "тараз": (42.9000, 71.3667),
    "джамбул": (42.9000, 71.3667),
    "taraz": (42.9000, 71.3667),
    # Pavlodar
    "павлодар": (52.2873, 76.9674),
    "pavlodar": (52.2873, 76.9674),
    # Ust-Kamenogorsk / Oskemen
    "усть-каменогорск": (49.9480, 82.6279),
    "оскемен": (49.9480, 82.6279),
    "ust-kamenogorsk": (49.9480, 82.6279),
    "oskemen": (49.9480, 82.6279),
    # Semey
    "семей": (50.4111, 80.2275),
    "семипалатинск": (50.4111, 80.2275),
    "semey": (50.4111, 80.2275),
    "semipalatinsk": (50.4111, 80.2275),
    # Atyrau
    "атырау": (47.1167, 51.8833),
    "гурьев": (47.1167, 51.8833),
    "atyrau": (47.1167, 51.8833),
    # Kostanay
    "костанай": (53.2198, 63.6354),
    "кустанай": (53.2198, 63.6354),
    "kostanay": (53.2198, 63.6354),
    "qostanay": (53.2198, 63.6354),
    # Kyzylorda
    "кызылорда": (44.8333, 65.5000),
    "кзыл-орда": (44.8333, 65.5000),
    "kyzylorda": (44.8333, 65.5000),
    "qyzylorda": (44.8333, 65.5000),
    # Uralsk / Oral
    "уральск": (51.2333, 51.3667),
    "орал": (51.2333, 51.3667),
    "uralsk": (51.2333, 51.3667),
    "oral": (51.2333, 51.3667),
    # Petropavlovsk
    "петропавловск": (54.8833, 69.1500),
    "петропавл": (54.8833, 69.1500),
    "petropavlovsk": (54.8833, 69.1500),
    # Aktau
    "актау": (43.6500, 51.1667),
    "шевченко": (43.6500, 51.1667),
    "aktau": (43.6500, 51.1667),
    "aqtau": (43.6500, 51.1667),
    # Temirtau
    "темиртау": (50.0500, 72.9667),
    "temirtau": (50.0500, 72.9667),
    # Turkestan
    "туркестан": (43.3000, 68.2500),
    "turkestan": (43.3000, 68.2500),
    # Kokshetau
    "кокшетау": (53.2833, 69.3833),
    "кокчетав": (53.2833, 69.3833),
    "kokshetau": (53.2833, 69.3833),
    "kokchetav": (53.2833, 69.3833),
    # Taldykorgan
    "талдыкорган": (45.0167, 78.3667),
    "taldykorgan": (45.0167, 78.3667),
    # Ekibastuz
    "экибастуз": (51.7167, 75.3167),
    "ekibastuz": (51.7167, 75.3167),
    # Rudny
    "рудный": (52.9667, 63.1333),
    "rudny": (52.9667, 63.1333),
    # Zhezkazgan
    "жезказган": (47.7833, 67.7000),
    "джезказган": (47.7833, 67.7000),
    "zhezkazgan": (47.7833, 67.7000),
    # Kaskelen
    "каскелен": (43.2000, 76.6167),
    "kaskelen": (43.2000, 76.6167),
    # Balkhash
    "балхаш": (46.8500, 74.9833),
    "balkhash": (46.8500, 74.9833),
    # Satpayev
    "сатпаев": (47.9000, 67.5333),
    "satpayev": (47.9000, 67.5333),
    # Kapshagay / Konayev
    "капшагай": (43.8833, 77.0833),
    "капчагай": (43.8833, 77.0833),
    "конаев": (43.8833, 77.0833),
    "kapshagay": (43.8833, 77.0833),
    "konayev": (43.8833, 77.0833),
    # Ridder
    "риддер": (50.3333, 83.5167),
    "лениногорск": (50.3333, 83.5167),
    "ridder": (50.3333, 83.5167),
    # Schuchinsk
    "щучинск": (52.9333, 70.2000),
    "schuchinsk": (52.9333, 70.2000),
    # Stepnogorsk
    "степногорск": (52.3500, 71.9833),
    "stepnogorsk": (52.3500, 71.9833),
    # Ayagoz
    "аягоз": (47.9667, 80.4333),
    "ayagoz": (47.9667, 80.4333),
    # Kentau
    "кентау": (43.5167, 68.5167),
    "kentau": (43.5167, 68.5167),
    # Saran
    "сарань": (49.7833, 73.1500),
    "saran": (49.7833, 73.1500),
    # Aksay
    "аксай": (51.1667, 53.0333),
    "aksay": (51.1667, 53.0333),
    # Arkalyk
    "аркалык": (50.2500, 66.9167),
    "arkalyk": (50.2500, 66.9167),
    # Baikonur
    "байконур": (45.6167, 63.3167),
    "байконыр": (45.6167, 63.3167),
    "baikonur": (45.6167, 63.3167),
    # Zhanaozen
    "жанаозен": (43.3500, 52.8667),
    "новый узень": (43.3500, 52.8667),
    "zhanaozen": (43.3500, 52.8667),
    # Shakhtinsk
    "шахтинск": (49.7167, 72.5833),
    "shakhtinsk": (49.7167, 72.5833),
    # Kulsary
    "кульсары": (46.9500, 54.0167),
    "kulsary": (46.9500, 54.0167),
    # Lisakovsk
    "лисаковск": (52.5500, 62.5000),
    "lisakovsk": (52.5500, 62.5000),
    # Aksу
    "аксу": (52.0333, 76.9167),
    "aksu": (52.0333, 76.9167),
    # Zharkent
    "жаркент": (44.1667, 80.0000),
    "панфилов": (44.1667, 80.0000),
    "zharkent": (44.1667, 80.0000),
    # Tekeli
    "текели": (44.8500, 78.7500),
    "tekeli": (44.8500, 78.7500),
    # Saryagash
    "сарыагаш": (41.4500, 69.1667),
    "saryagash": (41.4500, 69.1667),
    # Zyryanovsk / Altai
    "зыряновск": (49.7333, 84.2667),
    "алтай": (49.7333, 84.2667),
    "zyryanovsk": (49.7333, 84.2667),
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two coordinates using Haversine formula."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class GeocodingService:
    """Service for geocoding addresses to coordinates."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "FIRE-TicketRoutingSystem/1.0 (freedom-finance-routing)"

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": self.USER_AGENT}
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def geocode(self, address: str) -> Optional[GeoLocation]:
        """
        Geocode an address using cascade:
        1. Try Nominatim OSM API
        2. Fall back to Kazakhstan city dictionary
        """
        if not address or not address.strip():
            return None

        logger.info(f"🌍 Геокодинг: '{address}'")

        # Try Nominatim first
        logger.info("   🔍 [1] Пробую Nominatim OSM API...")
        nominatim_result = await self._geocode_nominatim(address)
        if nominatim_result:
            logger.info(f"   ✅ Nominatim: {nominatim_result.city} ({nominatim_result.latitude:.4f}, {nominatim_result.longitude:.4f})")
            return nominatim_result

        # Fall back to dictionary
        logger.info("   🔍 [2] Nominatim не дал результат, пробую словарь городов КЗ...")
        dict_result = self._geocode_dictionary(address)
        if dict_result:
            logger.info(f"   ✅ Словарь: {dict_result.city} ({dict_result.latitude:.4f}, {dict_result.longitude:.4f})")
            return dict_result

        logger.info("   ⚠️  Город не найден ни в одном источнике")
        return None

    async def _geocode_nominatim(self, address: str) -> Optional[GeoLocation]:
        """Query Nominatim OSM API for coordinates."""
        try:
            client = await self._get_client()

            # Add Kazakhstan country hint for better results
            search_query = address
            if "казахстан" not in address.lower() and "kazakhstan" not in address.lower():
                search_query = f"{address}, Казахстан"

            params = {
                "q": search_query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            }

            response = await client.get(self.NOMINATIM_URL, params=params)
            response.raise_for_status()

            data = response.json()
            if not data:
                return None

            result = data[0]
            lat = float(result["lat"])
            lon = float(result["lon"])

            # Extract city from address details
            address_details = result.get("address", {})
            city = (
                address_details.get("city")
                or address_details.get("town")
                or address_details.get("village")
                or address_details.get("municipality")
            )

            logger.info(f"   📍 Nominatim ответил: '{address}' → ({lat:.4f}, {lon:.4f}), город: {city}")

            return GeoLocation(
                latitude=lat,
                longitude=lon,
                city=city,
                source="nominatim"
            )

        except httpx.TimeoutException:
            logger.warning(f"Nominatim timeout for address: {address}")
            return None
        except httpx.HTTPError as e:
            logger.warning(f"Nominatim HTTP error for '{address}': {e}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            logger.warning(f"Nominatim parse error for '{address}': {e}")
            return None

    def _geocode_dictionary(self, address: str) -> Optional[GeoLocation]:
        """Look up address in Kazakhstan city dictionary."""
        if not address:
            return None

        address_lower = address.lower()

        # Check each city name in the dictionary
        for city_name, (lat, lon) in KAZAKHSTAN_CITIES.items():
            if city_name in address_lower:
                logger.info(f"Dictionary geocoded '{address}' via city '{city_name}' -> ({lat}, {lon})")
                return GeoLocation(
                    latitude=lat,
                    longitude=lon,
                    city=city_name.capitalize(),
                    source="dictionary"
                )

        return None

    def determine_nearest_office(
        self,
        location: Optional[GeoLocation],
        country: Optional[str] = None,
    ) -> Tuple[str, float]:
        """
        Determine which of the 15 offices is nearest to the location.
        Returns (office_name, distance_km).
        If location is None or country is not Kazakhstan, returns ("unknown", -1)
        to trigger 50/50 split between Astana and Almaty.
        """
        if location is None:
            return ("unknown", -1)

        # Check if foreign address
        if country and country.lower() not in ("казахстан", "kazakhstan", "kz"):
            logger.info(f"Foreign country detected: {country}")
            return ("unknown", -1)

        # Find nearest office from all 15
        nearest_office = None
        min_distance = float("inf")

        for office_name, (lat, lon) in OFFICE_COORDINATES.items():
            dist = haversine(location.latitude, location.longitude, lat, lon)
            if dist < min_distance:
                min_distance = dist
                nearest_office = office_name

        if nearest_office:
            logger.info(f"Nearest office: {nearest_office} ({min_distance:.1f} km)")
            return (nearest_office, min_distance)

        return ("unknown", -1)

    def extract_city_from_text(self, text: str) -> Optional[str]:
        """Extract city name from ticket text using dictionary matching."""
        if not text:
            return None

        text_lower = text.lower()

        # Check each city name
        for city_name in KAZAKHSTAN_CITIES.keys():
            if city_name in text_lower:
                return city_name.capitalize()

        return None
