"""Fraud/anomaly model service for URTS and payout decisions."""

from __future__ import annotations

import logging
import os
import threading
import warnings
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
TARGET_FRAUD_CONTAMINATION = 0.2
EXTREME_FEATURE_FACTORS = {
    "claims_per_week": (3.0, 1.35),
    "claim_to_work_ratio": (0.08, 1.6),
    "zone_mismatch_score": (0.5, 1.4),
    "claim_time_variance": (12.0, 1.25),
}

_MODEL: Any | None = None
_SCALER: Any | None = None
_SCORE_SCALER: Any | None = None
_LOAD_ATTEMPTED = False
_LOCK = threading.Lock()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _artifact_paths() -> tuple[Path, Path, Path]:
    base = _repo_root() / "models"
    return (
        Path(os.getenv("FRAUD_MODEL_PATH", base / "fraud_model.pkl")),
        Path(os.getenv("FRAUD_SCALER_PATH", base / "fraud_scaler.pkl")),
        Path(os.getenv("FRAUD_SCORE_SCALER_PATH", base / "fraud_score_scaler.pkl")),
    )


def reset_model_cache() -> None:
    """Test helper for forcing a fresh lazy load."""
    global _MODEL, _SCALER, _SCORE_SCALER, _LOAD_ATTEMPTED
    with _LOCK:
        _MODEL = None
        _SCALER = None
        _SCORE_SCALER = None
        _LOAD_ATTEMPTED = False


def _fallback_result(features_dict: dict | None = None) -> dict:
    return {
        "anomaly_score": 0.0,
        "is_anomaly": False,
        "model_available": False,
        "features": features_dict or {},
    }


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _emphasize_extreme_features(features_dict: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float]]:
    tuned_features = dict(features_dict)
    applied_factors: dict[str, float] = {}

    for feature_name, (threshold, multiplier) in EXTREME_FEATURE_FACTORS.items():
        raw_value = float(tuned_features.get(feature_name, 0.0) or 0.0)
        if raw_value >= threshold:
            tuned_features[feature_name] = round(raw_value * multiplier, 4)
            applied_factors[feature_name] = multiplier

    return tuned_features, applied_factors


def _calibrate_anomaly_score(anomaly_score: float, features_dict: dict[str, Any]) -> tuple[float, float]:
    calibrated_score = anomaly_score
    score_boost = 0.0
    claims_per_week = float(features_dict.get("claims_per_week", 0.0) or 0.0)
    claim_to_work_ratio = float(features_dict.get("claim_to_work_ratio", 0.0) or 0.0)
    zone_mismatch_score = float(features_dict.get("zone_mismatch_score", 0.0) or 0.0)
    claim_time_variance = float(features_dict.get("claim_time_variance", 0.0) or 0.0)

    low_risk_profile = (
        claims_per_week < 2.0
        and claim_to_work_ratio < 0.05
        and zone_mismatch_score < 0.5
        and claim_time_variance < 8.0
    )
    moderate_risk_profile = (
        claims_per_week < 3.0
        and claim_to_work_ratio < 0.08
        and zone_mismatch_score < 0.5
        and claim_time_variance < 12.0
    )

    if low_risk_profile:
        calibrated_score *= 0.35
    elif moderate_risk_profile:
        calibrated_score *= 0.6
    elif zone_mismatch_score >= 0.5 and claims_per_week < 2.0 and claim_to_work_ratio < 0.05 and claim_time_variance < 8.0:
        calibrated_score *= 0.75

    if claims_per_week >= 3.0:
        score_boost += min(0.12, (claims_per_week - 2.0) * 0.03)
    if claim_to_work_ratio >= 0.08:
        score_boost += min(0.14, (claim_to_work_ratio - 0.08) * 2.0)
    if zone_mismatch_score >= 0.5:
        score_boost += 0.12 if claims_per_week >= 3.0 or claim_to_work_ratio >= 0.08 or claim_time_variance >= 12.0 else 0.04
    if claim_time_variance >= 12.0:
        score_boost += min(0.08, (claim_time_variance - 12.0) / 100.0)

    return round(_clamp(calibrated_score + score_boost), 4), round(score_boost, 4)


def _load_artifacts() -> tuple[Any, Any, Any] | tuple[None, None, None]:
    global _MODEL, _SCALER, _SCORE_SCALER, _LOAD_ATTEMPTED

    if _LOAD_ATTEMPTED:
        return _MODEL, _SCALER, _SCORE_SCALER

    with _LOCK:
        if _LOAD_ATTEMPTED:
            return _MODEL, _SCALER, _SCORE_SCALER

        model_path, scaler_path, score_scaler_path = _artifact_paths()
        try:
            import joblib
            from sklearn.exceptions import InconsistentVersionWarning

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", InconsistentVersionWarning)
                _MODEL = joblib.load(model_path)
                _SCALER = joblib.load(scaler_path)
                _SCORE_SCALER = joblib.load(score_scaler_path)
            logger.info(
                "fraud model loaded",
                extra={
                    "model_path": str(model_path),
                    "scaler_path": str(scaler_path),
                    "score_scaler_path": str(score_scaler_path),
                    "target_contamination": TARGET_FRAUD_CONTAMINATION,
                },
            )
        except Exception:
            _MODEL = None
            _SCALER = None
            _SCORE_SCALER = None
            logger.exception(
                "failed to load fraud model; using safe non-anomalous fallback",
                extra={
                    "model_path": str(model_path),
                    "scaler_path": str(scaler_path),
                    "score_scaler_path": str(score_scaler_path),
                },
            )
        finally:
            _LOAD_ATTEMPTED = True

    return _MODEL, _SCALER, _SCORE_SCALER


def evaluate_fraud(features_dict: dict) -> dict:
    """Evaluate fraud risk using the trained anomaly model."""
    model, scaler, score_scaler = _load_artifacts()
    if model is None or scaler is None or score_scaler is None:
        return _fallback_result(features_dict)

    try:
        import pandas as pd

        model_features, applied_factors = _emphasize_extreme_features(features_dict)
        input_df = pd.DataFrame([model_features])

        for col in scaler.feature_names_in_:
            if col not in input_df.columns:
                input_df[col] = 0
        input_df = input_df[scaler.feature_names_in_]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            scaled_input_array = scaler.transform(input_df)
        scaled_input_df = pd.DataFrame(scaled_input_array, columns=scaler.feature_names_in_)

        raw_anomaly_score = model.decision_function(scaled_input_df)[0]

        inverted_raw_score = -raw_anomaly_score
        score_input = [[inverted_raw_score]]
        if hasattr(score_scaler, "feature_names_in_"):
            score_input = pd.DataFrame(score_input, columns=score_scaler.feature_names_in_)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            scaled_anomaly_score = score_scaler.transform(score_input)[0][0]

        prediction = model.predict(scaled_input_df)[0]
        anomaly_score = _clamp(float(scaled_anomaly_score))
        anomaly_score, calibration_boost = _calibrate_anomaly_score(anomaly_score, model_features)
        is_anomaly = anomaly_score > 0.75

        return {
            "anomaly_score": anomaly_score,
            "is_anomaly": is_anomaly,
            "model_predicted_anomaly": bool(prediction == -1),
            "model_available": True,
            "features": features_dict,
            "model_features": model_features,
            "feature_emphasis": applied_factors,
            "calibration_boost": calibration_boost,
            "target_contamination": TARGET_FRAUD_CONTAMINATION,
        }
    except Exception:
        logger.exception(
            "fraud model evaluation failed; using safe non-anomalous fallback",
            extra={"features": features_dict},
        )
        return _fallback_result(features_dict)
