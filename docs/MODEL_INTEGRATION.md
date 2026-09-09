# Model integration

No trained model was supplied. The application works without one: provider forecasts remain available and disaster endpoints use transparent non-model rules. `/api/models/status` reports missing/disabled/loaded explicitly.

## Files

Place trusted training artifacts under `models/`:

- `weather_model.pkl`
- `disaster_model.pkl`
- `preprocessor.pkl` when needed
- `scaler.pkl`, `encoder.pkl`, `feature_names.json` may be retained as training artifacts, but are **not auto-applied** because their relationships and training order cannot safely be inferred.

Create `models/schema/weather.json` and/or `models/schema/disaster.json`, based on the adjacent example manifests. Supply the **exact ordered feature names**, all approximately 39 if that is the weather model's real contract. Never fill in a guessed list.

```json
{
  "features": ["exact_training_feature_1", "exact_training_feature_2"],
  "input_format": "dataframe",
  "preprocessing": "embedded",
  "probabilities_calibrated": false
}
```

Supported `input_format`: `array` or `dataframe`. Supported `preprocessing`: `embedded` (a complete trained pipeline), `none` (the model explicitly expects raw numeric inputs), or `preprocessor.pkl` (a trusted fitted transformation). Prefer a single sklearn Pipeline that includes imputation, encoding and scaling. Separate encoders/scalers must be composed using their exact training logic before enabling inference. The API does not infer categorical encodings or units.

Install the exact Python ML-library versions used during training into the project's virtual environment and record them in requirements. Enable `TRUSTED_MODELS=true` in the ignored `.env`, then restart. Pickle can execute code: only enable this for artifacts you have verified and trust. The adapter deliberately does not unpickle unknown files merely to inspect them.

## Validation

Named numeric inputs are reordered by the manifest. Missing, unexpected and nonfinite values fail validation. The adapter compares the model's available feature-count and feature-name metadata with its declared contract. DataFrame input requires pandas. Trained preprocessing and model libraries must be installed separately, using the versions matching the training environment.

`POST /api/predict/weather` and `/api/predict/disaster` accept:

```json
{"features":{"exact_training_feature_2":2.0,"exact_training_feature_1":1.0}}
```

Weather returns `prediction`, `mode`, `model_source` and nullable confidence. Disaster returns `event`, `risk`, `severity`, `recommendations`, `mode` and nullable confidence. A class label alone is not a calibrated risk, and does not automatically map to an emergency severity. Only declare `probabilities_calibrated=true` when the model actually has calibrated probability output. A future production integration needs validated label-to-severity mappings and a documented evaluation report.

The test suite exercises ordering and missing-feature rejection with a test model. Real artifact accuracy cannot be validated until actual trained files and metadata are supplied.
