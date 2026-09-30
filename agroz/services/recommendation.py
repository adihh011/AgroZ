"""
Agro Z recommendation engine.

The supplied project specifies a Random Forest / Scikit-Learn recommendation
workflow using N, P, K, pH, temperature and rainfall. This implementation
provides a deterministic fallback so the project works immediately, while
also exposing a RandomForest-style scoring layer suitable for later replacement
with a validated local training dataset.
"""

from math import exp
import os

try:
    import joblib
except Exception:
    joblib = None

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model", "crop_model.joblib")

CROP_PROFILES = {
    "Rice":     {"n": 90, "p": 40, "k": 40, "ph": 6.2, "temp": 27, "humidity": 82, "rain": 220},
    "Maize":    {"n": 120, "p": 55, "k": 45, "ph": 6.5, "temp": 25, "humidity": 65, "rain": 100},
    "Banana":   {"n": 100, "p": 80, "k": 50, "ph": 6.0, "temp": 26, "humidity": 80, "rain": 200},
    "Potato":   {"n": 80, "p": 55, "k": 70, "ph": 5.8, "temp": 20, "humidity": 70, "rain": 90},
    "Tomato":   {"n": 90, "p": 50, "k": 60, "ph": 6.0, "temp": 23, "humidity": 65, "rain": 90},
    "Cotton":   {"n": 100, "p": 50, "k": 50, "ph": 6.5, "temp": 27, "humidity": 60, "rain": 90},
    "Chickpea": {"n": 40, "p": 60, "k": 45, "ph": 6.5, "temp": 22, "humidity": 50, "rain": 70},
    "Mango":    {"n": 80, "p": 50, "k": 80, "ph": 6.5, "temp": 26, "humidity": 70, "rain": 120},
}

FERTILIZERS = {
    "Rice": [
        ("Urea", "Nitrogen source", "Use only when nitrogen is deficient and follow local soil-test/RDF guidance."),
        ("DAP", "Nitrogen + phosphorus", "Useful when both N and P need correction; avoid adding P when soil is already high."),
        ("MOP", "Potassium source", "Consider when soil potassium is low."),
        ("Compost / FYM", "Organic nutrient source", "Supports integrated nutrient management and soil organic matter.")
    ],
    "Maize": [
        ("Urea", "Nitrogen source", "Common N source; split nitrogen according to crop stage and local recommendation."),
        ("DAP", "Nitrogen + phosphorus", "Suitable when phosphorus is deficient and DAP fits the nutrient plan."),
        ("MOP", "Potassium source", "Consider when potassium is deficient."),
        ("Compost / FYM", "Organic nutrient source", "Use as part of an integrated nutrient plan.")
    ],
    "Banana": [
        ("MOP", "Potassium source", "Important where potassium is deficient; banana has substantial K demand."),
        ("Urea", "Nitrogen source", "Use only to correct nitrogen requirement."),
        ("DAP", "Nitrogen + phosphorus", "Use only where phosphorus is required."),
        ("Compost / FYM", "Organic nutrient source", "Useful for integrated nutrient management.")
    ],
    "Potato": [
        ("MOP", "Potassium source", "Consider where soil K is deficient and crop-specific guidance permits."),
        ("DAP", "Nitrogen + phosphorus", "Use when P is deficient and the N contribution is accounted for."),
        ("Urea", "Nitrogen source", "Use according to soil test and crop-stage recommendation."),
        ("Compost / FYM", "Organic nutrient source", "Supports soil health.")
    ],
    "Tomato": [
        ("NPK Complex", "Balanced N-P-K source", "Useful when more than one major nutrient is deficient."),
        ("Urea", "Nitrogen source", "Use only where N is deficient."),
        ("MOP", "Potassium source", "Consider where K is deficient."),
        ("Compost / FYM", "Organic nutrient source", "Use as part of integrated nutrient management.")
    ],
    "Cotton": [
        ("Urea", "Nitrogen source", "Use according to soil-test and crop-stage recommendation."),
        ("DAP", "Nitrogen + phosphorus", "Use where P is deficient and N contribution is accounted for."),
        ("MOP", "Potassium source", "Consider where K is deficient."),
        ("Compost / FYM", "Organic nutrient source", "Supports soil health.")
    ],
    "Chickpea": [
        ("SSP", "Phosphorus + sulphur", "Useful where P/S requirements are confirmed."),
        ("MOP", "Potassium source", "Consider only when K is deficient."),
        ("Compost / FYM", "Organic nutrient source", "Supports integrated nutrient management."),
    ],
    "Mango": [
        ("MOP", "Potassium source", "Consider where K is deficient."),
        ("NPK Complex", "Balanced N-P-K source", "Use when multiple nutrients require correction."),
        ("Compost / FYM", "Organic nutrient source", "Useful for long-term soil health."),
    ]
}

def _distance(value, target, scale):
    return abs(value - target) / scale

def recommend_crop(data):
    # If a validated Random Forest has been trained and placed in model/, use it.
    # Otherwise keep the transparent compatibility fallback so the demo works out of the box.
    if joblib and os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            features = [[data["n"], data["p"], data["k"], data["temperature"], data["humidity"], data["ph"], data["rainfall"]]]
            crop = str(model.predict(features)[0])
            confidence = None
            if hasattr(model, "predict_proba"):
                confidence = round(float(max(model.predict_proba(features)[0])) * 100, 1)
            return {"crop": crop, "confidence": confidence or 0.0, "alternatives": [], "mode": "Validated Random Forest model"}
        except Exception:
            pass

    scores = {}
    for crop, p in CROP_PROFILES.items():
        distance = (
            _distance(data["n"], p["n"], 100)
            + _distance(data["p"], p["p"], 70)
            + _distance(data["k"], p["k"], 70)
            + _distance(data["ph"], p["ph"], 2.0)
            + _distance(data["temperature"], p["temp"], 12)
            + _distance(data["humidity"], p["humidity"], 35)
            + _distance(data["rainfall"], p["rain"], 180)
        )
        scores[crop] = distance

    ordered = sorted(scores.items(), key=lambda x: x[1])
    best_crop, best_distance = ordered[0]
    # Confidence is a similarity indicator, not a validated accuracy percentage.
    confidence = max(55.0, min(97.0, 100.0 - best_distance * 12.0))
    alternatives = [
        {"crop": c, "score": round(max(0, 100 - d * 12), 1)}
        for c, d in ordered[1:4]
    ]
    return {
        "crop": best_crop,
        "confidence": round(confidence, 1),
        "alternatives": alternatives,
        "mode": "Agro Z crop compatibility engine (fallback until a validated model is installed)"
    }

def _status(value, low, high):
    if value < low:
        return "Low"
    if value > high:
        return "High"
    return "Adequate"

def fertilizer_advisory(crop, data):
    p = CROP_PROFILES.get(crop, CROP_PROFILES["Rice"])
    statuses = {
        "N": _status(data["n"], p["n"] * 0.75, p["n"] * 1.25),
        "P": _status(data["p"], p["p"] * 0.75, p["p"] * 1.25),
        "K": _status(data["k"], p["k"] * 0.75, p["k"] * 1.25),
    }

    recommendations = []
    if statuses["N"] == "Low":
        recommendations.append({"name": "Urea", "reason": "Nitrogen is below the crop profile range."})
    if statuses["P"] == "Low":
        recommendations.append({"name": "DAP / SSP", "reason": "Phosphorus is below the crop profile range; choose the source that matches the full nutrient plan."})
    if statuses["K"] == "Low":
        recommendations.append({"name": "MOP", "reason": "Potassium is below the crop profile range."})

    if not recommendations:
        recommendations.append({
            "name": "No major N-P-K correction indicated",
            "reason": "Major nutrients are within the demo crop-profile range. Confirm with a current soil test and local crop recommendation."
        })

    # Crop-specific preferred names are shown separately from deficiency logic.
    preferred = FERTILIZERS.get(crop, [])
    return {
        "crop": crop,
        "statuses": statuses,
        "recommendations": recommendations,
        "preferred_options": [
            {"name": x[0], "type": x[1], "note": x[2]} for x in preferred
        ],
        "notice": "Advisory only: final fertilizer dose should be based on a current soil test, crop stage and local recommended dose."
    }
