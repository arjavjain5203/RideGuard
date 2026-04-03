from fastapi import APIRouter
import random

router = APIRouter(prefix="/mock", tags=["Mock External APIs"])

MOCK_STATE = {
    "Koramangala": {"temp": 28, "rain": 0, "aqi": 80, "speed": 22},
    "Indiranagar": {"temp": 30, "rain": 2, "aqi": 110, "speed": 18},
    "HSR Layout": {"temp": 29, "rain": 0, "aqi": 90, "speed": 25},
}

@router.get("/weather")
def get_weather(zone: str):
    """Mock Weather API"""
    base = MOCK_STATE.get(zone, {"temp": 32, "rain": 0})
    return {
        "zone": zone,
        "temperature": base.get("temp") + random.uniform(-2, 2),
        "rainfall": base.get("rain") + random.uniform(0, 5)
    }

@router.get("/aqi")
def get_aqi(zone: str):
    """Mock AQI API"""
    base = MOCK_STATE.get(zone, {"aqi": 120})
    return {
        "zone": zone,
        "aqi": base.get("aqi") + random.randint(-10, 30)
    }

@router.get("/traffic")
def get_traffic(zone: str):
    """Mock Traffic API"""
    base = MOCK_STATE.get(zone, {"speed": 20})
    return {
        "zone": zone,
        "avg_speed": max(1.0, base.get("speed") + random.uniform(-5, 5))
    }

@router.post("/set-extreme")
def set_extreme_conditions(zone: str, event_type: str):
    """Helper to force extreme values for end-to-end trigger tests"""
    if zone not in MOCK_STATE:
        MOCK_STATE[zone] = {"temp": 30, "rain": 0, "aqi": 100, "speed": 20}
        
    if event_type == "rain":
        MOCK_STATE[zone]["rain"] = 18.0
    elif event_type == "flood":
        MOCK_STATE[zone]["rain"] = 65.0
        MOCK_STATE[zone]["speed"] = 3.0
    elif event_type == "heat":
        MOCK_STATE[zone]["temp"] = 43.0
    elif event_type == "aqi":
        MOCK_STATE[zone]["aqi"] = 320.0
        
    return {"status": "success", "zone": zone, "forced_event": event_type, "state": MOCK_STATE[zone]}
