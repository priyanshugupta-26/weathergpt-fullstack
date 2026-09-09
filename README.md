# WeatherGPT

A locally runnable weather intelligence platform with an interactive Earth, provider-backed forecasts, a grounded English/Hindi assistant, hazard screening, and personal dashboards.

## Start

**macOS:** double-click `START_WEATHERGPT.command`.

**Windows:** double-click `START_WEATHERGPT.bat`.

**Linux / terminal:** `./START_WEATHERGPT.sh`.

The launcher creates a virtual environment, installs dependencies only when their manifest changes, builds the frontend only when its inputs change, creates `.env` and the SQLite schema, starts the API, and opens **http://127.0.0.1:8000**. Keep the launcher window open; Ctrl+C stops the server. Windows also has `STOP_WEATHERGPT.bat`, which targets the launcher's recorded WeatherGPT process.

Prerequisites on a new machine: Python 3.11+ and Node 22.13+ with npm. Initial dependency installation and live weather require internet access. This workspace was built and tested with Python 3.13 and Node 22.22.2 on macOS. Windows launch scripts share the Python bootstrap, but have not been executed on a Windows host.

## What is implemented

- Responsive dark/light/system interface with all 13 primary routes.
- Location search, coordinate input, browser geolocation, and shared location context.
- Open-Meteo current model conditions, hourly and 7-day forecasts, charts and timestamps.
- Three.js Earth, factual country boundaries, regional wind vectors, rain/temperature/humidity/pressure/cloud cells, and USGS earthquake reports.
- Deterministic weather chat in English/Hindi; optional grounded OpenAI-compatible LLM adapter; browser speech input when available.
- Threshold-based local hazard screening, WebSocket updates, opt-in browser notifications while open.
- Historical charts/monthly summaries, agriculture guidance, aviation context, and marine forecasts where the provider responds.
- Argon2 authentication, opaque HttpOnly sessions, saved locations, private chat history, preferences and a role-protected admin panel.
- Validated, explicitly trusted ML adapters and a prediction workbench in the signed-in dashboard.
- Offline fallback page that never caches live alerts or private API data.

## Data honesty

Current conditions are numerical-model estimates, not measurements from a local station. `LIVE` means a successful current-provider response, with source and meteorological time shown. The globe's weather field is **25 samples on a 3° regional grid**, not global radar or high-resolution coverage. Wind particles interpolate actual vector components; their visual timescale is accelerated.

No fake weather or active disasters are silently substituted. Missing provider data stays unavailable. Cyclone tracks, storm tracks, official warning polygons, METAR/TAF, and global air-quality/ocean rasters are not connected. The selected-location marine and air-quality endpoints are implemented, but timed out during this machine's live tests. Weather, regional grid, USGS, and archive endpoints responded successfully.

Threshold alerts are **not official warnings**, probabilities, or an all-hazards risk assessment. No alert is not an all-clear. Crop, flight and marine views are decision support, not certified operational guidance.

## Pages

| Route | Purpose |
|---|---|
| `/` | Overview, current conditions, globe, forecast and assistant previews |
| `/globe` | Interactive Earth, layers and point inspection |
| `/forecast` | Hourly plots, 7-day outlook and detailed hourly table |
| `/chat` | Grounded assistant, conversation history and voice input |
| `/alerts` | Screening alerts, filters and USGS reports |
| `/climate` | Date-range archive charts and monthly statistics |
| `/agriculture` | Soil/environment context and fieldwork guidance |
| `/aviation` | Airport selection, visibility, gusts and pressure |
| `/marine` | Offshore selection and marine parameter forecasts |
| `/dashboard` | Saved locations, recent queries and prediction workbench |
| `/profile`, `/settings` | Identity, preferences and notifications |
| `/admin` | Protected operational status |

## Architecture and files

```text
backend/
  main.py             API, lifecycle, scheduler and WebSockets
  auth.py             Argon2 / opaque-session authentication
  config.py           Environment configuration
  database.py         SQLAlchemy schema and persistence
  schemas.py          Validated request contracts
  providers/          Weather, grid and hazard interfaces
  services/           Disaster screening and WeatherQueryEngine
frontend/
  app/views/          Lazy-loaded pages
  components/         Globe, charts, model workbench and UI primitives
  lib/                API client and shared application context
  public/             Boundaries, icons, manifest and offline shell
models/
  adapters/           Trusted model loading and validated feature ordering
  schema/             Explicit training manifests and examples
scripts/              Cross-platform launcher and HTTP diagnostics
tests/                Backend unit/integration coverage
docs/                 Architecture and model integration details
```

See [architecture](docs/ARCHITECTURE.md) and [model integration](docs/MODEL_INTEGRATION.md).

## API

Interactive OpenAPI documentation: **http://127.0.0.1:8000/docs**.

| Method | Path |
|---|---|
| GET | `/api/health` |
| GET | `/api/locations/search?q=Patna` |
| GET | `/api/weather/current`, `/api/weather/hourly`, `/api/weather/forecast` |
| GET | `/api/weather/history?start=YYYY-MM-DD&end=YYYY-MM-DD` |
| GET | `/api/weather/air-quality`, `/api/weather/marine` |
| GET | `/api/globe/grid`, `/api/earthquakes`, `/api/cyclones` |
| GET | `/api/alerts`, `/api/alerts/active` |
| POST | `/api/chat`, `/api/predict/weather`, `/api/predict/disaster` |
| GET | `/api/models/status`, `/api/providers/status` |
| POST | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` |
| GET/PATCH | `/api/profile` |
| GET/POST | `/api/locations/saved` |
| DELETE | `/api/locations/saved/{id}` |
| GET | `/api/chat/history`, `/api/admin` |
| WS | `/ws/alerts?latitude=...&longitude=...` |

Weather endpoints accept `latitude`, `longitude` and optional `name`. Current/hourly/forecast routes return the same normalized bundle so the frontend can change views without redundant requests. Errors are structured; tracebacks stay server-side.

## Authentication and administrator

Register through Profile; there are no hardcoded passwords. Normal accounts cannot access admin endpoints. An administrator can be seeded at startup using `ADMIN_EMAIL` and `ADMIN_PASSWORD` (minimum 12 characters) in `.env`. The local launcher also supports `--seed-admin` for a generated local-only administrator; its credentials are written to the ignored, permission-restricted `data/local-admin.txt`.

## Environment

Copying environment files manually is unnecessary: the launcher creates `.env` from `.env.example`. Optional settings:

| Setting | Default / purpose |
|---|---|
| `DATABASE_URL` | `sqlite:///./data/weathergpt.db` |
| `SCHEDULER_ENABLED` | `true`; disabled during tests |
| `REFRESH_SECONDS` | `600`; minimum scheduled interval 60 seconds |
| `PROVIDER_TIMEOUT` | 12 seconds per request, one retry |
| `SECURE_COOKIES` | `false` locally; enable behind HTTPS |
| `DEVELOPMENT_ORIGINS` | Explicit localhost Vite origins; set `[]` in production |
| `TRUSTED_MODELS` | `false`; never auto-unpickle untrusted files |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Optional admin seed |
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | Optional grounded language-model provider |

The LLM integration has not been live-tested because no key was supplied. Weather and disaster models are missing; the non-model path is tested. Confidence stays null unless the manifest explicitly declares calibrated probability output.

## Development and testing

Commands executed in this workspace:

```sh
.venv/bin/python -m pytest -q
npm --prefix frontend run build
npm --prefix frontend run dev
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
.venv/bin/python scripts/smoke.py
```

Development mode serves Vite at 5173 with API/WebSocket proxying to 8000. The normal launcher serves the built application entirely on 8000. Tests use an isolated temporary SQLite database and explicit weather fixtures; fixtures never enter the application UI. Browser smoke checks cover desktop and mobile routes, overflow, navigation and representative interactions. See `docs/VALIDATION.md` for the final results.

## Database and production

SQLite is zero-configuration and initialized idempotently. SQLAlchemy supports a PostgreSQL URL after adding its driver. PostGIS and multi-worker coordination are future integrations; no claim is made that this local build is already a production emergency service. Shared cache/pubsub, one scheduler leader, migrations, backups, TLS, secure cookies and deployment-specific secrets/rate limits are needed before public operation.

## Docker

A multi-stage Dockerfile builds the SPA and serves it with FastAPI as a non-root user. Compose binds localhost:8000 and persists SQLite in a named volume. Docker is optional. Its runtime could not be tested because the local Docker daemon was not running; the configuration is supplied without a successful-container claim.

## Troubleshooting

- **Provider unavailable:** core pages still render; use Retry. Coordinate search works independently of the external geocoder. Marine locations should be offshore.
- **Port 8000 already occupied:** stop the other process or existing WeatherGPT instance. The launcher recognizes a healthy existing WeatherGPT server.
- **Model disabled:** inspect `/api/models/status`; verify trust setting, manifest and matching training-library versions.
- **Notifications denied:** change the browser's permission yourself or use in-app alerts. The app never bypasses permission.
- **Voice unavailable:** continue typing; speech support varies by browser.
- **Offline:** no old alerts are replayed as live; reconnect and retry.

## Sources and attribution

- [Open-Meteo forecast documentation](https://open-meteo.com/en/docs)
- [Open-Meteo marine documentation](https://open-meteo.com/en/docs/marine-weather-api)
- [USGS GeoJSON feeds](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php)
- [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) public-domain country boundaries
- [GeoNames](https://www.geonames.org/) city gazetteer, CC BY 4.0; see `docs/DATA_SOURCES.md`

Provider usage and licensing limits still apply to a future public/commercial deployment.
