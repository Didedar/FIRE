import math


# All 15 Office coordinates (exact from spec)
OFFICE_COORDINATES = {
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

# Additional Kazakhstan cities (for reference)
KNOWN_CITIES = {
    **OFFICE_COORDINATES,
    "Нур-Султан": (51.1694, 71.4491),
    "Семей": (50.4111, 80.2275),
    "Темиртау": (50.0500, 72.9667),
    "Туркестан": (43.3000, 68.2500),
    "Талдыкорган": (45.0167, 78.3667),
    "Экибастуз": (51.7167, 75.3167),
    "Рудный": (52.9667, 63.1333),
    "Жезказган": (47.7833, 67.7000),
    "Каскелен": (43.2000, 76.6167),
    "Балкаш": (46.8500, 74.9833),
    "Сатпаев": (47.9000, 67.5333),
    "Капшагай": (43.8833, 77.0833),
    "Конаев": (43.8833, 77.0833),
    "Риддер": (50.3333, 83.5167),
    "Щучинск": (52.9333, 70.2000),
    "Степногорск": (52.3500, 71.9833),
    "Аягоз": (47.9667, 80.4333),
}

# Kazakhstan bounding box (rough)
KZ_BOUNDS = {
    "lat_min": 40.5,
    "lat_max": 55.5,
    "lon_min": 46.5,
    "lon_max": 87.5,
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


def is_in_kazakhstan(lat: float, lon: float) -> bool:
    """Check if coordinates fall within Kazakhstan bounding box."""
    return (
        KZ_BOUNDS["lat_min"] <= lat <= KZ_BOUNDS["lat_max"]
        and KZ_BOUNDS["lon_min"] <= lon <= KZ_BOUNDS["lon_max"]
    )


def find_nearest_office(
    client_lat: float | None,
    client_lon: float | None,
    offices: list[dict],
) -> dict | None:
    """
    Find the nearest office to the client.
    Returns None if client has no coordinates or is abroad.
    offices: list of dicts with keys 'id', 'name', 'latitude', 'longitude'
    """
    if client_lat is None or client_lon is None:
        return None

    if not is_in_kazakhstan(client_lat, client_lon):
        return None

    best = None
    best_dist = float("inf")
    for office in offices:
        if office["latitude"] is None or office["longitude"] is None:
            continue
        d = haversine(client_lat, client_lon, office["latitude"], office["longitude"])
        if d < best_dist:
            best_dist = d
            best = office

    return best
