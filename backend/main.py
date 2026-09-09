import asyncio
import contextlib
import json
import logging
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date, timedelta
from urllib.parse import urlparse
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import select, func, delete, text
from sqlalchemy.exc import IntegrityError
from .config import settings, ROOT
from .database import (
    initialize,
    Session,
    User,
    AuthSession,
    Location,
    ChatMessage,
    save_record,
)
from .auth import (
    hasher,
    token_hash,
    optional_user,
    require_user,
    require_admin,
    public_user,
)
from .schemas import (
    Coordinates,
    SavedLocationInput,
    Credentials,
    ChatRequest,
    PredictionRequest,
    ProfileUpdate,
)
from .providers.weather import client, earthquakes, grid, utcnow
from .providers.engine import weather_engine, weather_engine as provider
from .providers.imd import imd
from .providers.cap import cap_provider
from .services.fusion import AlertFusionEngine, active
from .ai.router import ai_router
from .extensions import router as extension_router
from .services.alerts import alerts_service
from .services.query import query_engine
from .services.prediction import model_alerts
from models.adapters.adapter import weather_model, disaster_model, FeatureBuilder
from .ml.router import router as ml_router, auto_retrain_config
from .ml.registry import model_registry
from .ml.ingestion import ingestion_service
from .ml.verification import verification_service
from .ml.training import training_service

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("weathergpt")
watched = {}
active_alerts = {}
websocket_clients = 0
requests_count = 0
recent_errors = deque(maxlen=30)
rate_windows = defaultdict(deque)


async def refresh_location(lat, lon, name):
    weather = await provider.weather(lat, lon)
    derived = alerts_service.evaluate(weather, name)
    modeled = model_alerts(weather, name)
    for alert in derived + modeled:
        alert["effective"] = utcnow()
        alert["priority"] = 4 if alert in modeled else 5
        alert["source_type"] = "ml" if alert in modeled else "derived"
    official = []
    if 6 <= lat <= 38 and 68 <= lon <= 98:
        for product in ("warnings", "nowcast"):
            result = await imd.fetch(product)
            official.extend(a for a in result["items"] if AlertFusionEngine.matches(a, {"name": name, "latitude": lat, "longitude": lon}))
    cap = [a for a in await cap_provider.refresh() if AlertFusionEngine.matches(a, {"name": name, "latitude": lat, "longitude": lon})]
    active_alerts[(lat, lon)] = AlertFusionEngine.fuse(official, cap, modeled, derived)
    return weather


async def scheduler():
    while True:
        try:
            for (lat, lon), name in list(watched.items())[:50]:
                await refresh_location(lat, lon, name)

            # ML Ingestion & Verification cycles
            with contextlib.suppress(Exception):
                await ingestion_service.ingest_live_pilot_network()
                verification_service.verify_pending_predictions()

                # Check auto-retraining criteria
                if auto_retrain_config["enabled"] and not training_service.is_training:
                    champ = model_registry.active_champion
                    obs_cnt = ingestion_service.get_observation_count()
                    trained_rows = champ.metadata.get("training_rows", 0) if champ else 0
                    if obs_cnt - trained_rows >= auto_retrain_config["min_new_rows"]:
                        log.info("Auto-retraining triggered: %d new rows accumulated.", obs_cnt - trained_rows)
                        loop = asyncio.get_running_loop()
                        loop.run_in_executor(None, training_service.run_training_job, "AUTO_RETRAIN", "HistGradientBoosting")
                        auto_retrain_config["last_retrain_at"] = utcnow()

            with Session.begin() as db:
                db.execute(delete(AuthSession).where(AuthSession.expires < time.time()))
            log.info("scheduler_refresh locations=%s", len(watched))
        except Exception as error:
            log.exception("scheduler_error")
            recent_errors.append(
                {
                    "time": utcnow(),
                    "type": type(error).__name__,
                    "component": "scheduler",
                }
            )
        await asyncio.sleep(max(60, settings.refresh_seconds))


@asynccontextmanager
async def lifespan(app):
    initialize()
    if client.client.is_closed:
        import httpx
        client.client = httpx.AsyncClient(timeout=settings.provider_timeout)
    for model in [weather_model, disaster_model]:
        model.load()

    # Initialize WeatherGPT Own Model Champion
    model_registry.load_active_champion()
    ingestion_service.ensure_locations_seeded()
    if ingestion_service.get_observation_count() < 40:
        asyncio.create_task(ingestion_service.bootstrap_historical_data(days_back=7))

    if settings.admin_email and settings.admin_password:
        if len(settings.admin_password) < 12:
            raise RuntimeError("ADMIN_PASSWORD must have at least 12 characters")
        with Session.begin() as db:
            if not db.scalar(
                select(User).where(User.email == settings.admin_email.lower())
            ):
                db.add(
                    User(
                        email=settings.admin_email.lower(),
                        name="Administrator",
                        password_hash=hasher.hash(settings.admin_password),
                        role="admin",
                    )
                )
    task = asyncio.create_task(scheduler()) if settings.scheduler_enabled else None
    log.info("startup database_ready=true scheduler=%s", settings.scheduler_enabled)
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    await client.close()


app = FastAPI(title="WeatherGPT API", version="1.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.include_router(extension_router)
app.include_router(ml_router)

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    return JSONResponse({"detail": [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in error.errors()]}, status_code=422)


@app.middleware("http")
async def security(request: Request, call_next):
    global requests_count
    requests_count += 1
    if request.method in ("POST", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if (
            origin
            and urlparse(origin).netloc != request.headers.get("host")
            and origin not in settings.development_origins
        ):
            return JSONResponse(
                {"detail": "Cross-origin mutation rejected"}, status_code=403
            )
        try:
            content_length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Invalid content length"}, status_code=400)
        if content_length > 32768:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
    if request.url.path.startswith("/api/"):
        group = "auth" if "/auth/" in request.url.path else "chat" if "/chat" in request.url.path else "api"
        key = (request.client.host if request.client else "unknown", group)
        bucket = rate_windows[key]
        now = time.monotonic()
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= (20 if group in ("auth", "chat") else 240):
            return JSONResponse(
                {"detail": "Too many requests. Try again in a minute."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        bucket.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(Exception)
async def unexpected(request, error):
    log.exception("request_error path=%s", request.url.path)
    recent_errors.append(
        {"time": utcnow(), "type": type(error).__name__, "component": request.url.path}
    )
    return JSONResponse(
        {"detail": "The service could not complete this request. Please try again."},
        status_code=500,
    )


@app.get("/api/health")
async def health():
    with Session() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok", "version": "1.0.0", "timestamp": utcnow()}


@app.get("/api/locations/search")
async def search(q: str = Query(min_length=2, max_length=120)):
    try:
        return {"results": await provider.search(q)}
    except RuntimeError as error:
        return {"results": [], "status": "unavailable", "message": str(error)}


@app.get("/api/weather/current")
@app.get("/api/weather/hourly")
@app.get("/api/weather/forecast")
async def weather(
    latitude: float = Query(25.5941, ge=-90, le=90),
    longitude: float = Query(85.1376, ge=-180, le=180),
    name: str = Query("Selected location", max_length=160),
):
    key = (round(latitude, 3), round(longitude, 3))
    watched[key] = name
    if len(watched) > 50:
        expired = next(iter(watched))
        watched.pop(expired)
        active_alerts.pop(expired, None)
    return await refresh_location(*key, name)


@app.get("/api/weather/history")
async def history(
    start: date,
    end: date,
    latitude: float = Query(25.5941, ge=-90, le=90),
    longitude: float = Query(85.1376, ge=-180, le=180),
):
    if (
        end < start
        or (end - start).days > 730
        or end > date.today() - timedelta(days=5)
        or start < date(1940, 1, 1)
    ):
        raise HTTPException(
            422, "Use a range of up to two years, from 1940 through five days ago."
        )
    return await provider.history(
        latitude, longitude, start.isoformat(), end.isoformat()
    )


@app.get("/api/weather/marine")
async def marine(coords: Coordinates = Depends()):
    return await provider.marine(coords.latitude, coords.longitude)


@app.get("/api/weather/air-quality")
async def air(coords: Coordinates = Depends()):
    return await provider.air(coords.latitude, coords.longitude)


@app.get("/api/globe/grid")
async def weather_grid(coords: Coordinates = Depends()):
    return await grid(coords.latitude, coords.longitude)


@app.get("/api/earthquakes")
async def quake():
    return await earthquakes()


@app.get("/api/cyclones")
async def cyclones():
    data = await imd.fetch("cyclone")
    events = [e for e in data["items"] if not e.get("stale")]
    return {**data, "events": events, "message": "No active IMD cyclone data" if not events else None}


@app.get("/api/alerts")
@app.get("/api/alerts/active")
async def alerts(coords: Coordinates = Depends()):
    lat, lon = round(coords.latitude, 3), round(coords.longitude, 3)
    data = await refresh_location(lat, lon, coords.name)
    return {
        "alerts": active_alerts.get((lat, lon), []),
        "status": data["status"],
        "source": "Open-Meteo + transparent threshold screening",
        "official_feed": imd.status()["status"],
        "timestamp": utcnow(),
    }


@app.websocket("/ws/alerts")
async def alerts_socket(ws: WebSocket):
    global websocket_clients
    origin = ws.headers.get("origin")
    if (
        origin
        and urlparse(origin).netloc != ws.headers.get("host")
        and origin not in settings.development_origins
    ):
        await ws.close(code=1008)
        return
    try:
        lat, lon = (
            float(ws.query_params.get("latitude", 25.5941)),
            float(ws.query_params.get("longitude", 85.1376)),
        )
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError()
    except ValueError:
        await ws.close(code=1008)
        return
    await ws.accept()
    websocket_clients += 1
    log.info("websocket_connected")
    try:
        while True:
            await ws.send_json(
                {
                    "type": "alerts",
                    "alerts": [a for a in active_alerts.get((round(lat, 3), round(lon, 3)), []) if active(a)],
                    "timestamp": utcnow(),
                }
            )
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=15)
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, RuntimeError):
        log.info("websocket_disconnected")
    finally:
        websocket_clients -= 1


@app.post("/api/chat")
async def chat(payload: ChatRequest, request: Request):
    result = await query_engine.answer(payload)
    user = optional_user(request)
    if user:
        with Session.begin() as db:
            for role, content in [
                ("user", payload.message),
                ("assistant", result["message"]),
            ]:
                db.add(
                    ChatMessage(
                        user_id=user.id,
                        conversation=payload.conversation,
                        role=role,
                        content=content,
                    )
                )
    return result


@app.get("/api/chat/history")
async def chat_history(user=Depends(require_user)):
    with Session() as db:
        records = db.scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.id.desc())
            .limit(100)
        ).all()
        return {
            "messages": [
                {
                    "role": r.role,
                    "content": r.content,
                    "conversation": r.conversation,
                    "created": r.created,
                }
                for r in reversed(records)
            ]
        }


@app.post("/api/predict/weather")
async def predict_weather(payload: PredictionRequest):
    try:
        result = weather_model.predict(payload.features)
    except ValueError as error:
        raise HTTPException(422, str(error))
    result = result or {
        "mode": "fallback",
        "prediction": None,
        "confidence": None,
        "model_source": "No trained model loaded",
        "message": "Use the provider forecast. No synthetic ML prediction is returned.",
    }
    save_record(f"prediction:weather:{time.time_ns()}", "model_prediction", result)
    return result


@app.post("/api/predict/disaster")
async def predict_disaster(payload: PredictionRequest):
    try:
        result = disaster_model.predict(payload.features)
    except ValueError as error:
        raise HTTPException(422, str(error))
    if result:
        result = {
            **result,
            "event": str(result["prediction"]),
            "risk": "model output",
            "severity": "INFO",
            "recommendations": [],
        }
    else:
        result = alerts_service.prediction(payload.features)
    save_record(f"prediction:disaster:{time.time_ns()}", "model_prediction", result)
    return result


SMART_CITIES = [
    {"name": "New Delhi", "latitude": 28.6139, "longitude": 77.2090, "state": "Delhi"},
    {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "state": "Maharashtra"},
    {"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "state": "West Bengal"},
    {"name": "Chennai", "latitude": 13.0827, "longitude": 80.2707, "state": "Tamil Nadu"},
    {"name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946, "state": "Karnataka"},
    {"name": "Hyderabad", "latitude": 17.3850, "longitude": 78.4867, "state": "Telangana"},
    {"name": "Patna", "latitude": 25.5941, "longitude": 85.1376, "state": "Bihar"},
    {"name": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714, "state": "Gujarat"},
    {"name": "Pune", "latitude": 18.5204, "longitude": 73.8567, "state": "Maharashtra"},
    {"name": "Jaipur", "latitude": 26.9124, "longitude": 75.7873, "state": "Rajasthan"},
    {"name": "Lucknow", "latitude": 26.8467, "longitude": 80.9462, "state": "Uttar Pradesh"},
    {"name": "Guwahati", "latitude": 26.1445, "longitude": 91.7362, "state": "Assam"},
    {"name": "Srinagar", "latitude": 34.0837, "longitude": 74.7973, "state": "Jammu & Kashmir"},
    {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245, "state": "Odisha"},
    {"name": "Thiruvananthapuram", "latitude": 8.5241, "longitude": 76.9366, "state": "Kerala"},
]


@app.post("/api/predict/auto/weather")
async def predict_auto_weather(coords: Coordinates = Depends()):
    weather = await weather_engine.weather(coords.latitude, coords.longitude)
    current = weather.get("current", {})
    features = FeatureBuilder.build_weather_features(current)
    pred_res = weather_model.predict(features) if weather_model.model is not None else None
    curr_temp = float(current.get("temperature_2m") or 28.0)
    if pred_res and pred_res.get("prediction") is not None:
        val = pred_res["prediction"]
        predicted_temp = float(val if isinstance(val, (int, float)) else list(val.values())[0])
        mode = "model"
        source = pred_res.get("model_source", "weather_model.pkl")
    else:
        tendency = float(features.get("pressure_tendency_3h") or 0.0)
        sin_h = float(features.get("sin_hour") or 0.0)
        delta = round((tendency * -0.35) + (sin_h * 0.8), 2)
        predicted_temp = round(curr_temp + delta, 2)
        mode = "deterministic_thermodynamic"
        source = "WeatherGPT Thermodynamic Predictor"

    delta = round(predicted_temp - curr_temp, 2)
    trajectory = (
        "WARMING SHARPLY ↗"
        if delta >= 0.5
        else "COOLING RAPIDLY ↘"
        if delta <= -0.5
        else "THERMALLY STABLE →"
    )

    return {
        "mode": mode,
        "source": source,
        "station": coords.name,
        "latitude": coords.latitude,
        "longitude": coords.longitude,
        "current_temp": curr_temp,
        "predicted_temp_next_hour": predicted_temp,
        "thermal_delta": delta,
        "trajectory": trajectory,
        "features_39": features,
        "confidence": pred_res.get("confidence") if pred_res else None,
        "timestamp": weather.get("timestamp")
        or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.post("/api/predict/auto/disaster")
async def predict_auto_disaster(coords: Coordinates = Depends()):
    weather = await weather_engine.weather(coords.latitude, coords.longitude)
    current = weather.get("current", {})
    telemetry = {
        "temp_2m": current.get("temperature_2m"),
        "precip_1h": current.get("precipitation"),
        "wind_speed_10m": current.get("wind_speed_10m"),
        "wind_gusts_10m": current.get("wind_gusts_10m"),
        "surface_pressure": current.get("surface_pressure"),
        "weather_code": current.get("weather_code"),
    }
    features = FeatureBuilder.build_disaster_features(telemetry)
    if disaster_model.model is not None:
        result = disaster_model.predict(features)
        if result:
            result = {
                **result,
                "event": str(result["prediction"]),
                "risk": "model output",
                "severity": "INFO",
                "recommendations": ["Review local meteorological advisories."],
            }
    else:
        result = alerts_service.prediction(features)
    return {
        **result,
        "features_20": features,
        "location": {"latitude": coords.latitude, "longitude": coords.longitude, "name": coords.name},
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.get("/api/city-monitor")
async def city_monitor():
    city_summaries = []
    for city in SMART_CITIES:
        try:
            w = await weather_engine.weather(city["latitude"], city["longitude"])
            c = w.get("current", {})
            temp = float(c.get("temperature_2m") or 25.0)
            rh = float(c.get("relative_humidity_2m") or 50.0)
            rain = float(c.get("precipitation") or 0.0)
            wind = float(c.get("wind_speed_10m") or 10.0)
            press = float(c.get("surface_pressure") or 1010.0)
            flood_risk = "HIGH" if rain >= 15 else "MODERATE" if rain >= 5 else "LOW"
            heat_risk = (
                "HIGH"
                if temp >= 40 or (temp >= 35 and rh >= 70)
                else "MODERATE"
                if temp >= 35
                else "LOW"
            )
            city_summaries.append({
                "name": city["name"],
                "state": city["state"],
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "temperature": temp,
                "relative_humidity": rh,
                "precipitation": rain,
                "wind_speed": wind,
                "pressure": press,
                "flood_risk": flood_risk,
                "heat_risk": heat_risk,
                "status": "online",
                "source": w.get("source", "Open-Meteo"),
                "timestamp": w.get("timestamp"),
            })
        except Exception:
            city_summaries.append({
                "name": city["name"],
                "state": city["state"],
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "status": "unavailable",
                "flood_risk": "UNDETERMINED",
                "heat_risk": "UNDETERMINED",
            })
    return {
        "cities": city_summaries,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.get("/api/models/status")
async def models():
    return {"models": [weather_model.status(), disaster_model.status()]}


@app.get("/api/providers/status")
async def providers():
    return {
        "providers": client.status,
        "default": "Open-Meteo",
        "imd": imd.status(),
        "ai": await ai_router.status(),
        "cap": cap_provider.status,
        "cyclone": imd.states.get("cyclone", {"status": "not_checked"}),
        "official_alerts": imd.status()["status"],
    }


@app.post("/api/auth/register", status_code=201)
async def register(payload: Credentials):
    with Session.begin() as db:
        user = User(
            email=payload.email.lower(),
            name=payload.name,
            password_hash=hasher.hash(payload.password),
        )
        db.add(user)
        try:
            db.flush()
        except IntegrityError:
            raise HTTPException(409, "Email is already registered")
        return public_user(user)


@app.post("/api/auth/login")
async def login(payload: Credentials, response: Response):
    with Session.begin() as db:
        user = db.scalar(select(User).where(User.email == payload.email.lower()))
        try:
            valid = hasher.verify(
                user.password_hash if user else DUMMY_HASH, payload.password
            )
        except (VerifyMismatchError, InvalidHashError):
            valid = False
        if not user or not valid:
            raise HTTPException(401, "Invalid email or password")
        token = secrets.token_urlsafe(32)
        db.add(
            AuthSession(
                token_hash=token_hash(token),
                user_id=user.id,
                expires=time.time() + settings.session_days * 86400,
            )
        )
        response.set_cookie(
            "wg_session",
            token,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            max_age=settings.session_days * 86400,
        )
        return public_user(user)


DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    with Session.begin() as db:
        db.execute(
            delete(AuthSession).where(
                AuthSession.token_hash
                == token_hash(request.cookies.get("wg_session", ""))
            )
        )
    response.delete_cookie("wg_session")
    return {"status": "signed out"}


@app.get("/api/profile")
async def profile(user=Depends(require_user)):
    return public_user(user)


@app.patch("/api/profile")
async def update_profile(payload: ProfileUpdate, user=Depends(require_user)):
    with Session.begin() as db:
        stored = db.get(User, user.id)
        stored.name = payload.name
        stored.preferences = json.dumps(payload.model_dump(exclude={"name"}))
        return public_user(stored)


@app.get("/api/locations/saved")
async def saved(user=Depends(require_user)):
    with Session() as db:
        return {
            "locations": [
                {
                    "id": l.id,
                    "name": l.name,
                    "latitude": l.latitude,
                    "longitude": l.longitude,
                    "district": l.district, "state": l.state, "radius_km": l.radius_km, "label": l.label,
                }
                for l in db.scalars(select(Location).where(Location.user_id == user.id))
            ]
        }


@app.post("/api/locations/saved", status_code=201)
async def save_location(payload: SavedLocationInput, user=Depends(require_user)):
    with Session.begin() as db:
        if (
            db.scalar(
                select(func.count())
                .select_from(Location)
                .where(Location.user_id == user.id)
            )
            or 0
        ) >= 20:
            raise HTTPException(422, "Maximum 20 saved locations")
        db.add(Location(user_id=user.id, **payload.model_dump()))
        try:
            db.flush()
        except IntegrityError:
            raise HTTPException(409, "Location already saved")
    return {"status": "saved"}


@app.delete("/api/locations/saved/{location_id}")
async def delete_location(location_id: int, user=Depends(require_user)):
    with Session.begin() as db:
        db.execute(
            delete(Location).where(
                Location.id == location_id, Location.user_id == user.id
            )
        )
    return {"status": "deleted"}


@app.get("/api/admin")
async def admin(user=Depends(require_admin)):
    with Session() as db:
        return {
            "health": "ok",
            "ai": await ai_router.status(),
            "imd": imd.status(),
            "websocket_clients": websocket_clients,
            "cap": cap_provider.status,
            "users": db.scalar(select(func.count()).select_from(User)),
            "requests": requests_count,
            "database": "connected",
            "providers": client.status,
            "models": [weather_model.status(), disaster_model.status()],
            "active_alerts": [a for group in active_alerts.values() for a in group],
            "recent_errors": list(recent_errors),
            "ingestion": {
                "scheduler": settings.scheduler_enabled,
                "interval_seconds": max(60, settings.refresh_seconds),
                "watched_locations": len(watched),
            },
        }


static = ROOT / "frontend" / "dist" / "client"
if static.exists():
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str):
    if path.startswith(("api/", "ws/")):
        raise HTTPException(404, "Not found")
    candidate = (static / path).resolve()
    if candidate.is_relative_to(static.resolve()) and candidate.is_file():
        return FileResponse(candidate)
    index = static / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        {"message": "WeatherGPT API is ready. Frontend build is not yet available."}
    )
