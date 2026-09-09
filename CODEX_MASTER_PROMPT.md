# WeatherGPT — Codex master implementation prompt

You are continuing an existing runnable WeatherGPT repository. Preserve the current UI routes and public API shape unless a migration is clearly documented.

## Product goal
Build a competition-grade, production-oriented WeatherGPT for India that combines real-time meteorological data, historical climate data, NWP products, disaster information, trained ML models, natural-language interaction, multilingual/voice access, 3D GIS visualisation and proactive alerts.

## Non-negotiable capabilities
1. Home page with clear product narrative, live snapshot and navigation.
2. Full-screen 3D globe with wind/rain/temperature/pressure/cyclone/earthquake layers.
3. Per-layer legends, timestamps, source, model confidence and location details.
4. Animated wind particles driven by real U/V grid values rather than random particles.
5. Forecast dashboard with hourly/daily charts and model-vs-source comparison.
6. Conversational assistant that uses tool calling; never invent weather values.
7. Hindi + at least 4 Indian-language UI/chat paths; ASR/TTS adapters.
8. Disaster engine combining official event feeds, thresholds and the user's trained disaster model.
9. Browser/mobile push alerts with user-defined location, radius and severity.
10. Climate analysis from the historical database with anomaly/trend calculations.
11. Agriculture, aviation, marine and urban advisories with safety disclaimers where appropriate.
12. User accounts, saved locations, preferences, alert rules and admin operations.
13. Model registry for weather + disaster model versions, metrics and feature schema.
14. PostgreSQL/PostGIS/TimescaleDB storage; migrations and seed data.
15. Scheduled/streaming ingestion with idempotency, retry, logging and data-quality checks.
16. Docker Compose local environment and production-ready environment variables.
17. Tests for API, ingestion, auth, model adapters and key frontend flows.
18. Documentation for local run, model integration, deployment and API contracts.

## Data model direction
Create normalized tables for users, locations, weather_observations, weather_forecasts, disaster_events, alert_rules, alert_events, model_versions, model_predictions, advisory_runs, api_sources and ingestion_runs. Add PostGIS geometry and time indexes where useful.

## Engineering rules
- Keep provider-specific logic behind adapters.
- Store source name, source timestamp, ingestion timestamp and units with weather values.
- Never train continuously on only the last few live hours and delete older data. Preserve historical training datasets/versioned snapshots.
- Inference must reuse the exact training preprocessing pipeline and feature ordering.
- All alert logic must be explainable: official warning / rule threshold / model probability.
- Make live feeds fail gracefully and expose freshness in the UI.
- Add structured logs and health/readiness endpoints.
- No secrets committed to git.

## First implementation milestone
Replace the current demo climate adapter and random globe particles with a PostgreSQL-backed gridded-data pipeline, while keeping the repository runnable with fallback demo data when external services are unavailable.
