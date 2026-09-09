import os
from pathlib import Path

try:
    import joblib
except Exception:
    joblib = None

WEATHER_MODEL_PATH = Path(os.getenv("WEATHER_MODEL_PATH", "./models/weather_model.pkl"))
DISASTER_MODEL_PATH = Path(os.getenv("DISASTER_MODEL_PATH", "./models/disaster_model.pkl"))
_models = {"weather": None, "disaster": None}

def load_models():
    if joblib:
        for name, path in [("weather", WEATHER_MODEL_PATH), ("disaster", DISASTER_MODEL_PATH)]:
            if path.exists():
                try: _models[name] = joblib.load(path)
                except Exception: _models[name] = None

def status():
    return {
        "weather_model": bool(_models["weather"]),
        "disaster_model": bool(_models["disaster"]),
        "weather_model_path": str(WEATHER_MODEL_PATH),
        "disaster_model_path": str(DISASTER_MODEL_PATH),
    }

def predict(kind: str, features: list[float]):
    model = _models.get(kind)
    if model is None:
        return {"loaded": False, "prediction": None, "message": f"Drop your {kind} model into models/ and restart."}
    try:
        pred = model.predict([features])
        value = pred[0].item() if hasattr(pred[0], "item") else pred[0]
        return {"loaded": True, "prediction": value}
    except Exception as exc:
        return {"loaded": True, "prediction": None, "error": str(exc)}
