from fastapi import APIRouter, Query

from app.services.disruption_model_service import (
    MODEL_PROBABILITY_THRESHOLD,
    get_critical_breaches,
    is_model_available,
    predict_disruption,
    should_trigger,
)

router = APIRouter(prefix="/api/ml", tags=["ML"])


@router.get("/predict")
def predict_disruption_endpoint(
    rainfall: float = Query(...),
    temperature: float = Query(...),
    aqi: float = Query(...),
    traffic_speed: float = Query(...),
):
    probability = predict_disruption(rainfall, temperature, aqi, traffic_speed)
    critical_breaches = get_critical_breaches(rainfall, temperature, aqi, traffic_speed)
    return {
        "probability": probability,
        "trigger": should_trigger(probability, rainfall, temperature, aqi, traffic_speed),
        "model_available": probability is not None or is_model_available(),
        "threshold": MODEL_PROBABILITY_THRESHOLD,
        "critical_breaches": list(critical_breaches.keys()),
    }
