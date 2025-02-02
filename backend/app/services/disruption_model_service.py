"""ML disruption prediction service with safe threshold fallback support."""

from __future__ import annotations

import logging
import os
import pickle
import threading
import warnings
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MODEL_PROBABILITY_THRESHOLD = 0.7
CRITICAL_THRESHOLDS = {
    "rainfall": 25.0,
    "aqi": 350.0,
    "temperature": 45.0,
    "traffic_speed": 3.0,
}

_MODEL: Any | None = None
_SCALER: Any | None = None
_LOAD_ATTEMPTED = False
_LOCK = threading.Lock()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _model_paths() -> tuple[Path, Path]:
    model_path = Path(os.getenv("DISRUPTION_MODEL_PATH", _repo_root() / "models" / "disruption_model.pkl"))
    scaler_path = Path(os.getenv("DISRUPTION_SCALER_PATH", _repo_root() / "models" / "scaler.pkl"))
    return model_path, scaler_path


def _load_artifact(path: Path) -> Any:
    try:
        import joblib
        from sklearn.exceptions import InconsistentVersionWarning

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InconsistentVersionWarning)
            return joblib.load(path)
    except ModuleNotFoundError:
        pass
    except Exception:
        logger.debug("joblib artifact load failed; retrying with pickle", extra={"path": str(path)}, exc_info=True)

    with path.open("rb") as artifact_file:
        return pickle.load(artifact_file)


def reset_model_cache() -> None:
    """Test helper for forcing a fresh lazy load."""
    global _MODEL, _SCALER, _LOAD_ATTEMPTED
    with _LOCK:
        _MODEL = None
        _SCALER = None
        _LOAD_ATTEMPTED = False


def _load_artifacts() -> tuple[Any, Any] | tuple[None, None]:
    global _MODEL, _SCALER, _LOAD_ATTEMPTED

    if _LOAD_ATTEMPTED:
        return _MODEL, _SCALER

    with _LOCK:
        if _LOAD_ATTEMPTED:
            return _MODEL, _SCALER

        model_path, scaler_path = _model_paths()
        try:
            _MODEL = _load_artifact(model_path)
            _SCALER = _load_artifact(scaler_path)
            logger.info(
                "disruption model loaded",
                extra={"model_path": str(model_path), "scaler_path": str(scaler_path)},
            )
        except Exception:
            _MODEL = None
            _SCALER = None
            logger.exception(
                "failed to load disruption model; falling back to threshold logic",
                extra={"model_path": str(model_path), "scaler_path": str(scaler_path)},
            )
        finally:
            _LOAD_ATTEMPTED = True

    return _MODEL, _SCALER


def is_model_available() -> bool:
    model, scaler = _load_artifacts()
    return model is not None and scaler is not None


def predict_disruption(rainfall: float, temperature: float, aqi: float, traffic_speed: float) -> float | None:
    """Return disruption probability, or None if the model is unavailable/fails."""
    model, scaler = _load_artifacts()
    if model is None or scaler is None:
        return None

    features = [[float(rainfall), float(temperature), float(aqi), float(traffic_speed)]]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            scaled = scaler.transform(features)
        if hasattr(model, "predict_proba"):
            probability = float(model.predict_proba(scaled)[0][1])
        else:
            probability = float(model.predict(scaled)[0])
        return max(0.0, min(1.0, probability))
    except Exception:
        logger.exception(
            "disruption model prediction failed; falling back to threshold logic",
            extra={
                "rainfall": rainfall,
                "temperature": temperature,
                "aqi": aqi,
                "traffic_speed": traffic_speed,
            },
        )
        return None


def get_environment_inputs(
    rainfall: float,
    temperature: float,
    aqi: float,
    traffic_speed: float,
) -> dict[str, float]:
    return {
        "rainfall": float(rainfall),
        "temperature": float(temperature),
        "aqi": float(aqi),
        "traffic_speed": float(traffic_speed),
    }


def get_critical_breaches(
    rainfall: float,
    temperature: float,
    aqi: float,
    traffic_speed: float,
) -> dict[str, float]:
    breaches: dict[str, float] = {}
    if rainfall >= CRITICAL_THRESHOLDS["rainfall"]:
        breaches["rain"] = float(rainfall)
    if aqi >= CRITICAL_THRESHOLDS["aqi"]:
        breaches["aqi"] = float(aqi)
    if temperature >= CRITICAL_THRESHOLDS["temperature"]:
        breaches["heat"] = float(temperature)
    if traffic_speed <= CRITICAL_THRESHOLDS["traffic_speed"]:
        breaches["flood"] = float(traffic_speed)
    return breaches


def get_dominant_ml_trigger_type(
    rainfall: float,
    temperature: float,
    aqi: float,
    traffic_speed: float,
) -> tuple[str, float]:
    traffic_risk = max(0.0, (10.0 - float(traffic_speed)) / 7.0)
    scores = {
        "rain": (float(rainfall) / CRITICAL_THRESHOLDS["rainfall"], float(rainfall)),
        "heat": (float(temperature) / CRITICAL_THRESHOLDS["temperature"], float(temperature)),
        "aqi": (float(aqi) / CRITICAL_THRESHOLDS["aqi"], float(aqi)),
        "flood": (traffic_risk, float(traffic_speed)),
    }
    trigger_type, (_, trigger_value) = max(scores.items(), key=lambda item: item[1][0])
    return trigger_type, trigger_value


def should_trigger(probability: float | None, rainfall: float, temperature: float, aqi: float, traffic_speed: float) -> bool:
    return bool(
        (probability is not None and probability > MODEL_PROBABILITY_THRESHOLD)
        or get_critical_breaches(rainfall, temperature, aqi, traffic_speed)
    )
