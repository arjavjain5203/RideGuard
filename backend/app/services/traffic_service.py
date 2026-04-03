import random

def get_traffic(zone: str):
    """Mock Traffic API. Returns traffic_speed_kmh."""
    base_speed = 30.0
    
    if zone == "Silk Board":
        base_speed = random.uniform(2.0, 15.0)
        
    return {
        "traffic_speed_kmh": max(0.0, base_speed + random.uniform(-5.0, 10.0))
    }
