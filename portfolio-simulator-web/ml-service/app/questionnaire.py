from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np

from .paths import MODEL_ARTIFACTS_ROOT

MODEL_PATH = MODEL_ARTIFACTS_ROOT / "questionnaire-risk-tolerance" / "risk_tolerance_rf_model.pkl"

FEATURE_NAMES = [
    "age",
    "Duration_Score",
    "Expect_Score",
    "Monitor_Score",
    "gender_Male",
    "Objective_Growth",
    "Objective_Income",
    "Purpose_Savings for Future",
    "What are your savings objectives?_Health Care",
]

DURATION_SCORE = {
    "Less than 1 year": 1,
    "1-3 years": 2,
    "3-5 years": 3,
    "More than 5 years": 4,
}
EXPECT_SCORE = {"10%-20%": 1, "20%-30%": 2, "30%-40%": 3}
MONITOR_SCORE = {"Monthly": 1, "Weekly": 2, "Daily": 3}

LABEL_NAMES = {0: "Conservative", 1: "Moderate", 2: "Aggressive"}
RISK_LEVELS = {0: "low", 1: "medium", 2: "high"}

_MODEL: Any | None = None


def questionnaire_model_available() -> bool:
    return MODEL_PATH.exists()


def build_feature_vector(questionnaire: dict[str, Any]) -> list[float]:
    try:
        age = int(questionnaire["age"])
        duration = str(questionnaire["Duration"])
        expect = str(questionnaire["Expect"])
        monitor = str(questionnaire["Invest_Monitor"])
        gender = str(questionnaire["gender"])
        objective = str(questionnaire["Objective"])
        purpose = str(questionnaire["Purpose"])
        savings_objective = str(questionnaire["What are your savings objectives?"])
    except KeyError as exc:
        raise ValueError(f"Missing questionnaire field: {exc.args[0]}") from exc

    if duration not in DURATION_SCORE:
        raise ValueError(f"Unsupported Duration value: {duration}")
    if expect not in EXPECT_SCORE:
        raise ValueError(f"Unsupported Expect value: {expect}")
    if monitor not in MONITOR_SCORE:
        raise ValueError(f"Unsupported Invest_Monitor value: {monitor}")

    return [
        float(age),
        float(DURATION_SCORE[duration]),
        float(EXPECT_SCORE[expect]),
        float(MONITOR_SCORE[monitor]),
        1.0 if gender == "Male" else 0.0,
        1.0 if objective == "Growth" else 0.0,
        1.0 if objective == "Income" else 0.0,
        1.0 if purpose == "Savings for Future" else 0.0,
        1.0 if savings_objective == "Health Care" else 0.0,
    ]


def _load_model() -> Any:
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing risk-tolerance model at {MODEL_PATH}")
    _MODEL = joblib.load(MODEL_PATH)
    return _MODEL


def predict_questionnaire_risk(questionnaire: dict[str, Any]) -> dict[str, Any]:
    model = _load_model()
    features = build_feature_vector(questionnaire)
    values = np.asarray([features], dtype=float)
    predicted_class = int(model.predict(values)[0])
    probabilities_array = model.predict_proba(values)[0]
    classes = [int(value) for value in getattr(model, "classes_", [0, 1, 2])]
    probabilities = {
        LABEL_NAMES[class_id]: float(probabilities_array[index])
        for index, class_id in enumerate(classes)
        if class_id in LABEL_NAMES
    }
    aggressive_probability = probabilities.get("Aggressive", 0.0)
    return {
        "riskClass": predicted_class,
        "riskLabel": LABEL_NAMES[predicted_class],
        "riskLevel": RISK_LEVELS[predicted_class],
        "probabilities": probabilities,
        "riskScore": float(aggressive_probability * 100.0),
    }
