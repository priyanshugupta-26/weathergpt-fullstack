import asyncio
import contextlib
import json
import logging
import re
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone, timedelta
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
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
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
    now,
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
    RegisterInput,
    LoginInput,
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
from .services.alerts import alerts_service, india_alert_aggregator
from .services.notifications import notifications_service
from .providers.gfs import gfs_provider, wrf_provider
from .providers.bhashini import bhashini_provider
from .services.wis2 import wis2_consumer
from .services.climate import climate_service
from .routers.system_status import router as system_status_router
from .services.query import query_engine
from .services.prediction import model_alerts
from models.adapters.adapter import weather_model, disaster_model, FeatureBuilder
from .ml.router import router as ml_router, auto_retrain_config
from .routers.data_lab import router as data_lab_router
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
        client.client = httpx.AsyncClient(
            timeout=settings.provider_timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 WeatherGPT/1.0",
                "Accept": "application/json, text/plain, */*",
            },
            follow_redirects=True,
        )
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
    wis2_consumer.start_background()
    task = asyncio.create_task(scheduler()) if settings.scheduler_enabled else None
    log.info("startup database_ready=true scheduler=%s wis2=%s", settings.scheduler_enabled, wis2_consumer.is_connected)
    yield
    wis2_consumer.stop()
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    with contextlib.suppress(Exception):
        await client.close()


app = FastAPI(title="WeatherGPT API", version="1.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.include_router(extension_router)
app.include_router(ml_router)
app.include_router(data_lab_router)
app.include_router(system_status_router)

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    return JSONResponse({"detail": [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in error.errors()]}, status_code=422)


@app.middleware("http")
async def security(request: Request, call_next):
    global requests_count
    requests_count += 1

    origin = request.headers.get("origin")
    is_allowed_origin = False
    if origin:
        host = request.headers.get("host")
        parsed = urlparse(origin)
        if (
            (host and parsed.netloc == host)
            or origin in settings.development_origins
            or parsed.hostname in ("localhost", "127.0.0.1")
            or parsed.scheme in ("capacitor", "ionic")
        ):
            is_allowed_origin = True

    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": origin or "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept, Origin, X-Requested-With",
                "Access-Control-Max-Age": "86400",
            },
        )

    if request.method in ("POST", "PATCH", "DELETE"):
        if origin and not is_allowed_origin:
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

    if is_allowed_origin and origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

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
    source: str = Query("auto", max_length=50),
):
    key = (round(latitude, 3), round(longitude, 3))
    watched[key] = name
    if len(watched) > 50:
        expired = next(iter(watched))
        watched.pop(expired)
        active_alerts.pop(expired, None)

    s_clean = source.strip().lower()
    if s_clean in ("weathergpt_ml", "weathergpt ml", "ml", "own_model", "own-model"):
        from backend.services.prediction import generate_ml_weather_forecast
        return generate_ml_weather_forecast(latitude, longitude, name)
    elif s_clean in ("open-meteo", "open_meteo", "openmeteo"):
        return await provider.weather(latitude, longitude)
    elif s_clean == "imd":
        imd_res = await imd.forecast(latitude, longitude)
        if imd_res and imd_res.get("status") == "live":
            return imd_res

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
async def quake(scope: str = "india"):
    return await earthquakes(scope=scope)


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


@app.get("/api/alerts/aggregated")
@app.get("/api/disasters/feed")
async def get_aggregated_disasters(
    scope: str = "india",
    latitude: float | None = None,
    longitude: float | None = None,
    district: str | None = None,
    state: str | None = None,
):
    return await india_alert_aggregator.aggregate(
        latitude=latitude,
        longitude=longitude,
        district=district,
        state=state,
        scope=scope,
    )


# ----------------------------------------------------
# Push Notifications & In-App Notification Center
# ----------------------------------------------------

@app.get("/api/notifications/vapid-key")
@app.get("/api/notifications/vapid-public-key")
async def get_vapid_public_key():
    return {
        "public_key": notifications_service.public_key,
        "publicKey": notifications_service.public_key,
    }


@app.post("/api/notifications/subscribe")
async def subscribe_push(payload: dict, user = Depends(require_user)):
    sub_data = payload.get("subscription") or payload
    dev_name = payload.get("device_name", "Web Browser")
    try:
        return notifications_service.subscribe_user(user.id, sub_data, dev_name)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/notifications/unsubscribe")
async def unsubscribe_push(payload: dict, user = Depends(require_user)):
    endpoint = payload.get("endpoint", "")
    if endpoint:
        notifications_service.unsubscribe_user(user.id, endpoint)
    return {"status": "unsubscribed"}


@app.get("/api/notifications")
async def list_notifications(
    unread_only: bool = False,
    category: str | None = None,
    limit: int = 50,
    user = Depends(require_user),
):
    items = notifications_service.get_in_app_notifications(
        user_id=user.id,
        unread_only=unread_only,
        category=category,
        limit=limit,
    )
    unread_count = len([i for i in items if not i["is_read"]])
    return {"notifications": items, "unread_count": unread_count}


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int, user = Depends(require_user)):
    notifications_service.mark_as_read(user.id, notification_id)
    return {"status": "ok"}


@app.post("/api/notifications/read-all")
async def mark_all_notifications_read(user = Depends(require_user)):
    notifications_service.mark_all_read(user.id)
    return {"status": "ok"}


@app.delete("/api/notifications/{notification_id}")
async def delete_notification(notification_id: int, user = Depends(require_user)):
    notifications_service.delete_notification(user.id, notification_id)
    return {"status": "ok"}


@app.post("/api/notifications/test-dispatch")
async def test_dispatch_notification(user = Depends(require_user)):
    test_alert = {
        "id": f"test:{int(time.time())}",
        "headline": "Severe Thunderstorm Warning",
        "severity": "WARNING",
        "event": "Thunderstorm with Lightning Likely",
        "instruction": "Take shelter inside sturdy buildings. Avoid open fields and tall trees.",
        "location": user.district or user.city or "Registered Location",
        "source": "IMD / NDMA Sachet",
        "expires": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
    }
    delivered = notifications_service.deliver_alert_to_user(test_alert, user.id, user.city or "Your Location")
    return {"status": "dispatched", "delivered": delivered}


# ----------------------------------------------------
# Native Mobile & FCM Push Endpoints (Sections 10-12, 20, 71)
# ----------------------------------------------------

@app.post("/api/push/register-device")
async def register_push_device(payload: dict, user = Depends(require_user)):
    platform = payload.get("platform", "android")
    device_token = payload.get("device_token") or payload.get("token")
    device_name = payload.get("device_name", "Android Device")
    p256dh = payload.get("p256dh")
    auth = payload.get("auth")
    if not device_token:
        raise HTTPException(400, "device_token is required")
    try:
        return notifications_service.register_device(
            user_id=user.id,
            platform=platform,
            device_token=device_token,
            device_name=device_name,
            p256dh=p256dh,
            auth=auth,
        )
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/push/unregister-device")
async def unregister_push_device(payload: dict, user = Depends(require_user)):
    device_token = payload.get("device_token") or payload.get("token")
    if not device_token:
        raise HTTPException(400, "device_token is required")
    return notifications_service.unregister_device(user.id, device_token)


@app.get("/api/push/devices")
async def list_push_devices(user = Depends(require_user)):
    return {"devices": notifications_service.get_user_devices(user.id)}


@app.post("/api/push/test")
async def send_test_push(payload: dict | None = None, user = Depends(require_user)):
    data = payload or {}
    target_user_id = user.id
    if user.role == "admin" and data.get("user_id"):
        target_user_id = int(data["user_id"])
    target_token = data.get("device_token")
    title = data.get("title") or "WeatherGPT Test Notification"
    message = data.get("message") or "This confirms Android push notifications are working."
    return notifications_service.send_test_push(
        user_id=target_user_id,
        device_token=target_token,
        title=title,
        message=message,
    )


@app.get("/api/push/status")
async def push_status(user = Depends(require_user)):
    return notifications_service.get_system_push_status()



# ----------------------------------------------------
# Numerical Weather Prediction (NWP) - GFS & WRF
# ----------------------------------------------------

@app.get("/api/nwp/gfs")
async def get_gfs_nwp(latitude: float = 25.5941, longitude: float = 85.1376, forecast_hours: int = 48):
    return await gfs_provider.get_forecast(latitude, longitude, forecast_hours)


@app.get("/api/nwp/wrf")
async def get_wrf_status():
    return wrf_provider.status()


# ----------------------------------------------------
# Multi-Decade Climate Reanalysis (10, 20, 30 Years)
# ----------------------------------------------------

@app.get("/api/climate/multi-decade")
async def get_multi_decade_climate(latitude: float = 25.5941, longitude: float = 85.1376, years: int = 10):
    return await climate_service.get_multi_decade_analysis(latitude, longitude, years=years)


# ----------------------------------------------------
# BHASHINI Multilingual AI
# ----------------------------------------------------

@app.get("/api/bhashini/status")
async def get_bhashini_status():
    return bhashini_provider.status()


@app.post("/api/bhashini/translate")
async def bhashini_translate(payload: dict):
    text = payload.get("text", "")
    src = payload.get("source_language", "en")
    tgt = payload.get("target_language", "hi")
    return await bhashini_provider.translate(text, src, tgt)


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


@app.websocket("/ws/data-stream")
async def data_stream_socket(ws: WebSocket):
    global websocket_clients
    origin = ws.headers.get("origin")
    if (
        origin
        and urlparse(origin).netloc != ws.headers.get("host")
        and origin not in settings.development_origins
    ):
        await ws.close(code=1008)
        return
    await ws.accept()
    websocket_clients += 1
    log.info("data_stream_websocket_connected")
    last_sent_id = None
    try:
        from backend.services.data_lab import data_lab_service
        while True:
            stats = data_lab_service.get_top_summary_stats()
            recent = data_lab_service.get_paginated_observations(page=1, page_size=20)
            latest_id = recent["items"][0]["id"] if recent["items"] else None
            is_new = latest_id != last_sent_id if last_sent_id is not None else False
            last_sent_id = latest_id

            await ws.send_json(
                {
                    "type": "data_stream_telemetry",
                    "is_new_event": is_new,
                    "stats": stats,
                    "recent_observations": recent["items"],
                    "timestamp": utcnow(),
                }
            )

            try:
                msg_text = await asyncio.wait_for(ws.receive_text(), timeout=3.0)
                try:
                    msg = json.loads(msg_text)
                    if msg.get("action") == "trigger_ingest":
                        loc_name = msg.get("location", "Patna")
                        from backend.routers.data_lab import trigger_live_ingestion
                        await trigger_live_ingestion(location=loc_name)
                except Exception:
                    pass
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, RuntimeError):
        log.info("data_stream_websocket_disconnected")
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
                        conversation=payload.conversation or "default",
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


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", str(phone)).strip()
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    return cleaned if cleaned else None


@app.post("/api/auth/register", status_code=201)
async def register(payload: RegisterInput, response: Response):
    if payload.confirm_password is not None and payload.password != payload.confirm_password:
        raise HTTPException(400, "Passwords do not match")
    if len(payload.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    clean_email = payload.email.strip().lower()
    full_name = (payload.full_name or payload.name or "Explorer").strip()
    norm_mobile = normalize_phone(payload.mobile or payload.mobile_number)

    with Session.begin() as db:
        existing = db.scalar(select(User).where(User.email == clean_email))
        if existing:
            raise HTTPException(409, "An account with this email already exists.")

        pref_loc = None
        if payload.latitude is not None and payload.longitude is not None:
            pref_loc = {
                "name": payload.city or payload.district or "Patna",
                "latitude": payload.latitude,
                "longitude": payload.longitude,
                "country": "India",
            }

        user = User(
            email=clean_email,
            name=full_name,
            password_hash=hasher.hash(payload.password),
            mobile=norm_mobile,
            preferred_language=payload.preferred_language or "en",
            state=payload.state or "",
            district=payload.district or "",
            city=payload.city or "",
            latitude=payload.latitude,
            longitude=payload.longitude,
            preferences=json.dumps({
                "language": payload.preferred_language or "en",
                "default_location": pref_loc,
            }),
            last_login=now(),
        )
        db.add(user)
        try:
            db.flush()
        except IntegrityError:
            raise HTTPException(409, "An account with this email already exists.")

        # Automatic login upon registration
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
        user_data = public_user(user)
        user_data["token"] = token
        return user_data


@app.post("/api/auth/login")
async def login(payload: LoginInput, response: Response):
    identifier = (payload.email or payload.mobile or "").strip()
    if not identifier:
        raise HTTPException(400, "Email or mobile number is required")
    norm_phone = normalize_phone(identifier)

    with Session.begin() as db:
        query = select(User).where(User.email == identifier.lower())
        if norm_phone:
            query = select(User).where(
                (User.email == identifier.lower()) | (User.mobile == norm_phone)
            )
        user = db.scalar(query)
        try:
            valid = hasher.verify(
                user.password_hash if user else DUMMY_HASH, payload.password
            )
        except (VerifyMismatchError, InvalidHashError):
            valid = False
        if not user or not valid:
            raise HTTPException(401, "Invalid email or password")
        user.last_login = now()
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
        user_data = public_user(user)
        user_data["token"] = token
        return user_data


DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("wg_session", "")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
    if token:
        with Session.begin() as db:
            db.execute(
                delete(AuthSession).where(
                    AuthSession.token_hash == token_hash(token)
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
        if not stored:
            raise HTTPException(404, "User not found")
        if payload.name is not None:
            stored.name = payload.name
        if payload.mobile is not None:
            stored.mobile = normalize_phone(payload.mobile)
        lang = (
            payload.preferred_language
            or payload.language
            or (payload.preferences.get("language") if payload.preferences else None)
            or stored.preferred_language
        )
        if lang:
            stored.preferred_language = lang
        if payload.state is not None:
            stored.state = payload.state
        if payload.district is not None:
            stored.district = payload.district
        if payload.city is not None:
            stored.city = payload.city
        if payload.default_location:
            stored.latitude = payload.default_location.latitude
            stored.longitude = payload.default_location.longitude
        stored.updated_at = now()

        prefs = {}
        if stored.preferences:
            try:
                prefs = json.loads(stored.preferences)
            except Exception:
                prefs = {}
        dumped = payload.model_dump(
            exclude={"name", "mobile", "state", "district", "city", "preferences"},
            exclude_none=True,
        )
        prefs.update(dumped)
        if payload.preferences:
            prefs.update(payload.preferences)
        if lang:
            prefs["language"] = lang
        stored.preferences = json.dumps(prefs)
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


PROTECTED_PORTAL_ROUTES = {
    "/dashboard",
    "/globe",
    "/forecast",
    "/chat",
    "/alerts",
    "/climate",
    "/agriculture",
    "/aviation",
    "/marine",
    "/city-monitor",
    "/model-lab",
    "/data-lab",
    "/settings",
    "/profile",
    "/saved-locations",
    "/notifications",
    "/system-status",
}


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str, request: Request):
    if path.startswith(("api/", "ws/")):
        raise HTTPException(404, "Not found")

    candidate = (static / path).resolve()
    if candidate.is_relative_to(static.resolve()) and candidate.is_file():
        return FileResponse(candidate)

    index = static / "index.html"
    norm_path = "/" + path.strip("/")
    user = optional_user(request)

    # 1. Root route
    if norm_path == "/":
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        return RedirectResponse(url="/dashboard", status_code=302)

    # 2. Registration and Login routes
    if norm_path in ("/register", "/login"):
        if user:
            return RedirectResponse(url="/dashboard", status_code=302)
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"message": "WeatherGPT Authentication is ready."})

    # 3. Onboarding route
    if norm_path == "/onboarding":
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"message": "WeatherGPT Onboarding is ready."})

    # 4. Admin & Setup routes
    if norm_path == "/setup":
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        if user.role != "admin":
            raise HTTPException(403, "Administrator access required")
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"message": "WeatherGPT Setup is ready."})

    if norm_path == "/admin":
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        if user.role != "admin":
            raise HTTPException(403, "Administrator access required")
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"message": "WeatherGPT Admin is ready."})

    # 5. Protected portal routes
    if norm_path in PROTECTED_PORTAL_ROUTES or any(norm_path.startswith(p + "/") for p in PROTECTED_PORTAL_ROUTES):
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"message": "WeatherGPT Portal is ready."})

    # 6. Fallback
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        {"message": "WeatherGPT API is ready. Frontend build is not yet available."}
    )
