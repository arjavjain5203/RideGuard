import random
from app.utils import normalize

def evaluate_event(rider_id: str, zone: str) -> dict:
    """
    Behavioral Risk Engine.
    Simulates signals: gps_anomaly, cluster_risk, activity_mismatch, device_risk
    Returns normalized values and the final Event Adjustment point penalty.
    """
    raw_gps = random.uniform(0.0, 10.0)
    raw_cluster = random.uniform(0.0, 50.0)
    raw_activity = random.uniform(0.0, 5.0)
    raw_device = random.uniform(0.0, 1.0)

    gps_anomaly = normalize(raw_gps, 0.0, 10.0)
    cluster_risk = normalize(raw_cluster, 10.0, 50.0)
    activity_mismatch = normalize(raw_activity, 0.0, 5.0)
    device_risk = normalize(raw_device, 0.0, 1.0)

    penalty = -1 * (
        (0.30 * gps_anomaly) +
        (0.30 * cluster_risk) +
        (0.25 * activity_mismatch) +
        (0.15 * device_risk)
    ) * 50.0

    return {
        "signals": {
            "gps_anomaly": round(gps_anomaly, 2),
            "cluster_risk": round(cluster_risk, 2),
            "activity_mismatch": round(activity_mismatch, 2),
            "device_risk": round(device_risk, 2)
        },
        "event_adjustment": round(penalty, 0)
    }
