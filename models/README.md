# Model integration

Put your trained files here:

- `weather_model.pkl`
- `disaster_model.pkl`

WeatherGPT loads them automatically at startup with `joblib`. The generic `/api/models/predict` endpoint accepts a numeric feature vector. For a real model, edit `services/model_service.py` so the feature ordering and preprocessing exactly match your training pipeline. Best practice: export the complete sklearn `Pipeline`, not only the estimator.
