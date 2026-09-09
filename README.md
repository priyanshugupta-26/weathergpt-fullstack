# WeatherGPT — Full-stack runnable starter

A production-style WeatherGPT starter with:

- Home / marketing page
- Interactive 3D atmospheric globe with layer controls
- Live weather from Open-Meteo with deterministic offline fallback
- 24-hour forecast dashboard
- Conversational AI shell with location context + browser voice input
- Live alert center over WebSockets + browser notification permission
- Climate analytics adapter
- Agriculture / aviation / marine / public advisories
- SQLite demo authentication + admin console
- Plug-in adapters for your trained weather and disaster `.pkl` models
- Mobile-responsive UI

## Run locally

```powershell
cd weathergpt_fullstack
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open: `http://127.0.0.1:8000`

Demo admin:

- Email: `admin@weathergpt.local`
- Password: `admin123`

Change the demo credential before deployment.

## Your models

Copy your exported sklearn pipelines into:

```text
models/weather_model.pkl
models/disaster_model.pkl
```

Then edit `services/model_service.py` to enforce your exact 39-feature / disaster-feature ordering. If you trained preprocessing separately, export a complete sklearn `Pipeline` to avoid train/serve mismatch.

## Recommended production migration

1. Replace SQLite with PostgreSQL + PostGIS/TimescaleDB.
2. Add ingestion workers for Open-Meteo/IMD/WIS2.0/GFS/WRF/satellite/disaster feeds.
3. Store raw data and cleaned/feature-engineered data in separate schemas/tables.
4. Serve model predictions through dedicated versioned inference endpoints.
5. Add Redis + Celery/RQ/Kafka for background ingestion and alert fanout.
6. Add Firebase Cloud Messaging / Web Push + service worker for device alerts.
7. Add an LLM provider with tool calling to weather, forecast, alerts and climate endpoints.
8. Add multilingual translation/ASR/TTS service.
9. Add raster/vector tiles or gridded NetCDF/Zarr adapters for true globe layers.
10. Containerize and deploy behind Nginx / managed Kubernetes or a simpler PaaS for the hackathon.

## Important

The 3D layer in this starter is a real WebGL globe, but it visualises synthetic atmospheric particles around the live selected-location observation. For true India/world weather density, the next Codex task is to ingest gridded values (e.g. wind U/V, rainfall, temperature) and map them to particle speed, altitude, size and colour per coordinate.
