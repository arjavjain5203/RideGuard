import random

def get_weather(zone: str):
    """Mock weather API. Returns rainfall_mm_hr and temperature_c."""
    # In a real app, this would use an external API like OpenWeatherMap
    base_rain = 0.0
    base_temp = 32.0
    
    if zone == "Koramangala":
        base_rain = random.uniform(0.0, 5.0)
    elif zone == "Indiranagar":
        base_temp = random.uniform(34.0, 43.0)
        
    return {
        "rainfall_mm_hr": base_rain + random.uniform(0.0, 10.0),
        "temperature_c": base_temp + random.uniform(-2.0, 5.0)
    }
