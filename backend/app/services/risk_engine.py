"""Risk Engine — zone risk scoring and dynamic premium adjustment."""

from app.config import settings


# Environmental risk weight factors
RISK_WEIGHTS = {
    "rain": 0.35,
    "temp": 0.25,
    "aqi": 0.25,
    "traffic": 0.15,
}


def normalize_rainfall(mm_hr: float) -> float:
    """Normalize rainfall to 0-1 scale (0=dry, 1=≥25 mm/hr)."""
    return min(mm_hr / 25.0, 1.0)


def normalize_temperature(temp_c: float) -> float:
    """Normalize temperature to 0-1 scale (0=≤30°C, 1=≥45°C)."""
    if temp_c <= 30:
        return 0.0
    return min((temp_c - 30) / 15.0, 1.0)


def normalize_aqi(aqi: float) -> float:
    """Normalize AQI to 0-1 scale (0=≤50, 1=≥400)."""
    if aqi <= 50:
        return 0.0
    return min((aqi - 50) / 350.0, 1.0)


def normalize_traffic(speed_kmh: float) -> float:
    """Normalize traffic to 0-1 scale (0=free flow ≥40 km/h, 1=gridlock ≤5 km/h)."""
    if speed_kmh >= 40:
        return 0.0
    if speed_kmh <= 5:
        return 1.0
    return 1.0 - (speed_kmh - 5) / 35.0


def calculate_zone_risk_score(
    rainfall_mm_hr: float = 0.0,
    temperature_c: float = 30.0,
    aqi: float = 50.0,
    traffic_speed_kmh: float = 30.0,
) -> float:
    """
    Calculate composite risk score for a zone (0.0 - 1.0).
    Risk Score = 0.35×R_rain + 0.25×R_temp + 0.25×R_aqi + 0.15×R_traffic
    """
    r_rain = normalize_rainfall(rainfall_mm_hr)
    r_temp = normalize_temperature(temperature_c)
    r_aqi = normalize_aqi(aqi)
    r_traffic = normalize_traffic(traffic_speed_kmh)

    score = (
        RISK_WEIGHTS["rain"] * r_rain
        + RISK_WEIGHTS["temp"] * r_temp
        + RISK_WEIGHTS["aqi"] * r_aqi
        + RISK_WEIGHTS["traffic"] * r_traffic
    )
    return round(score, 4)


def get_premium_multiplier(risk_score: float) -> float:
    """Dynamic premium multiplier based on zone risk score."""
    if risk_score > 0.7:
        return 1.30  # High-risk zone surcharge
    elif risk_score < 0.3:
        return 0.85  # Low-risk zone discount
    return 1.00


def get_zone_multiplier(zone: str) -> float:
    """Lookup zone-specific multiplier for Bangalore areas."""
    return settings.ZONE_MULTIPLIERS.get(
        zone.lower().replace(" ", "_"),
        settings.ZONE_MULTIPLIERS["default"],
    )
