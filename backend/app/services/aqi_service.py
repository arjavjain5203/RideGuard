import random

def get_aqi(zone: str):
    """Mock AQI API. Returns AQI."""
    base_aqi = 100.0
    
    if zone == "Whitefield":
        base_aqi = random.uniform(150.0, 250.0)
        
    return {
        "aqi": base_aqi + random.uniform(-20.0, 100.0)
    }
