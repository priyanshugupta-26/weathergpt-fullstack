"""Local setup, official products, NWP, research and monitoring routes."""
import asyncio
import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlparse
from dotenv import dotenv_values
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from .config import ROOT, Settings, settings
from .auth import require_admin, optional_user
from .schemas import Coordinates, ChatRequest
from .database import Session, ChatMessage, Record, save_record
from .ai.router import ai_router
from .services.query import query_engine
from .providers.imd import imd
from .providers.nwp import GFSProvider, WRFProvider
from .providers.engine import weather_engine
from .services.fusion import active
from models.adapters.adapter import weather_model, disaster_model

router = APIRouter()
setup_lock = asyncio.Lock()


def require_local(request: Request):
    host = urlparse("http://" + request.headers.get("host", "")).hostname
    if settings.app_env != "development" or not request.client or request.client.host not in ("127.0.0.1", "::1") or host not in ("127.0.0.1", "localhost", "::1"):
        raise HTTPException(403, "Setup is available only on localhost in development")
    if request.headers.get("forwarded") or request.headers.get("x-forwarded-for"):
        raise HTTPException(403, "Setup cannot be accessed through a proxy")
    if request.method != "GET":
        origin = request.headers.get("origin", "")
        if origin != str(request.base_url).rstrip("/") or request.headers.get("x-weathergpt-setup") != "1":
            raise HTTPException(403, "Same-origin setup request required")


class SetupInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    groq_api_key: str | None = Field(None, max_length=512, repr=False, pattern=r"^[^\r\n\x00]*$")
    gemini_api_key: str | None = Field(None, max_length=512, repr=False, pattern=r"^[^\r\n\x00]*$")
    imd_token: str | None = Field(None, max_length=2048, repr=False, pattern=r"^[^\r\n\x00]*$")
    groq_model: str | None = Field(None, max_length=150, pattern=r"^[a-zA-Z0-9/_.-]*$")
    gemini_model: str | None = Field(None, max_length=150, pattern=r"^[a-zA-Z0-9/_.-]*$")
    ai_provider: Literal["auto", "groq", "gemini", "deterministic"] | None = None
    imd_auth_header: Literal["Authorization", "X-API-Key", "api-key"] | None = None
    imd_auth_scheme: Literal["Bearer", ""] | None = None


@router.get("/api/setup/status")
async def setup_status(request: Request):
    allowed = True
    try:
        require_local(request)
    except HTTPException:
        allowed = False
    return {"local_setup_allowed": allowed, "groq": bool(settings.groq_api_key),
            "gemini": bool(settings.gemini_api_key), "imd": bool(settings.imd_token),
            "selection": settings.ai_provider, "groq_model": settings.groq_model,
            "gemini_model": settings.gemini_model}


def require_setup_access(request: Request):
    require_local(request)
    user = optional_user(request)
    if not user:
        raise HTTPException(401, "Sign in as administrator to configure credentials")
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required to configure API credentials")


@router.post("/api/setup", dependencies=[Depends(require_setup_access)])
async def setup(payload: SetupInput):
    async with setup_lock:
        path = ROOT / ".env.local"
        old = dict(dotenv_values(path)) if path.exists() else {}
        changes = payload.model_dump(exclude_none=True)
        for key, value in changes.items():
            # Blank secret fields preserve an existing credential.
            if key.endswith(("api_key", "token")) and not value:
                continue
            old[key.upper()] = value
        fd, tmp = tempfile.mkstemp(prefix=".env.local-", dir=ROOT)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w") as stream:
                for key, value in old.items():
                    # dotenv single-quoted values do not interpolate user dollars.
                    escaped = str(value or "").replace("\\", "\\\\").replace("'", "\\'")
                    stream.write(f"{key}='{escaped}'\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        fresh = Settings()
        for key in SetupInput.model_fields:
            setattr(settings, key, getattr(fresh, key))
        imd.cache.clear()
        imd.states.clear()
        imd.blocked_until = 0
        await ai_router.configure()
    return {"status": "saved", "message": "Provider settings saved server-side. Blank secrets were preserved."}


@router.get("/api/ai/status")
async def ai_status():
    return await ai_router.status()


@router.post("/api/ai/check", dependencies=[Depends(require_local)])
async def ai_check():
    return await ai_router.status(check=True)


@router.get("/api/providers/imd/status")
async def imd_status():
    if not imd.states:
        await imd.fetch("current")
    return imd.status()


@router.get("/api/imd/{product}")
async def imd_product(product: str, id: str | None = Query(None, max_length=80),
                      latitude: float = Query(25.5941, ge=-90, le=90),
                      longitude: float = Query(85.1376, ge=-180, le=180)):
    params = {"id": id} if id else None
    if product == "sunmoon":
        params = {"lat": latitude, "lon": longitude}
    try:
        result = await imd.fetch(product, params)
    except ValueError:
        raise HTTPException(404, "Unknown IMD product")
    if product in ("warnings", "nowcast", "subdivision_warnings"):
        result = {**result, "active_items": [a for a in result["items"] if active(a)]}
    return result


@router.get("/api/nwp/{model}")
async def nwp(model: Literal["gfs", "wrf"], coords: Coordinates = Depends()):
    return await (GFSProvider() if model == "gfs" else WRFProvider()).forecast(coords.latitude, coords.longitude)


@router.post("/api/chat/stream")
async def stream_chat(payload: ChatRequest, request: Request):
    user = optional_user(request)
    async def events():
        result = await query_engine.prepare(payload)
        context = {"message": payload.message, "language": result["query"]["language"],
                   "data": result.pop("tool_context", {}), "fallback": result["message"]}
        text = ""
        mode = "deterministic"
        yield "data: " + json.dumps({"type": "context", "result": {**result, "message": ""}}, ensure_ascii=False) + "\n\n"
        async for event in ai_router.stream(context):
            if await request.is_disconnected():
                return
            if event["type"] == "reset":
                text = ""
            elif event["type"] == "delta":
                text += event["text"]
                mode = event["provider"]
            yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
        if user:
            with Session.begin() as db:
                for role, content in (("user", payload.message), ("assistant", text)):
                    db.add(ChatMessage(user_id=user.id, conversation=payload.conversation, role=role, content=content))
        yield "data: " + json.dumps({"type": "done", "mode": mode}) + "\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


class MonitorInput(BaseModel):
    points: list[Coordinates] = Field(min_length=1, max_length=6)


@router.post("/api/city-monitor")
async def city_monitor(payload: MonitorInput):
    async def monitor(point):
        weather, air = await asyncio.gather(weather_engine.weather(point.latitude, point.longitude), weather_engine.air(point.latitude, point.longitude))
        c = weather.get("current", {})
        rain = c.get("precipitation")
        return {"location": point.model_dump(), "weather": weather, "air": air,
                "waterlogging_signal": "Rainfall signal; drainage and ground data required" if rain is not None and rain >= 10 else "Not assessed: drainage data unavailable"}
    return {"points": await asyncio.gather(*(monitor(p) for p in payload.points))}


class TravelInput(BaseModel):
    origin: Coordinates
    destination: Coordinates
    departure: datetime


@router.post("/api/travel")
async def travel(payload: TravelInput):
    if not payload.departure.tzinfo:
        raise HTTPException(422, "Departure requires timezone")
    if not datetime.now(timezone.utc)-timedelta(hours=1) <= payload.departure <= datetime.now(timezone.utc)+timedelta(days=6):
        raise HTTPException(422, "Departure must be within the forecast horizon")
    a, b = payload.origin, payload.destination
    points = [a, Coordinates(latitude=(a.latitude+b.latitude)/2, longitude=(a.longitude+b.longitude)/2, name="Straight-line midpoint"), b]
    results = []
    for p in points:
        w = await weather_engine.weather(p.latitude, p.longitude)
        from zoneinfo import ZoneInfo
        def delta(row):
            t = datetime.fromisoformat(row["time"])
            t = t.replace(tzinfo=t.tzinfo or ZoneInfo(w.get("timezone", "UTC")))
            return abs((t-payload.departure).total_seconds())
        nearest = min(w["hourly"], key=delta) if w["hourly"] else None
        results.append({"location": p.model_dump(), "forecast": nearest, "source": w["source"], "status": w["status"]})
    return {"points": results, "message": "Three straight-line samples at departure time. Not a road route, road closure feed or travel safety guarantee."}


@router.get("/api/brief")
async def brief(coords: Coordinates = Depends()):
    return await query_engine.answer(ChatRequest(**coords.model_dump(), message="Give me today's weather and travel advisory"))


@router.get("/api/model-lab")
async def model_lab():
    with Session() as db:
        records = db.scalars(select(Record).where(Record.kind == "model_evaluation").order_by(Record.created.desc()).limit(100)).all()
        evaluations = [json.loads(r.payload) for r in records]
    return {"models": [weather_model.status(), disaster_model.status()], "evaluations": evaluations,
            "message": "Metrics require paired predictions and observed outcomes. Missing models never produce synthetic scores."}


class EvaluationInput(BaseModel):
    model: Literal["weather", "disaster"]
    variable: str = Field(min_length=1, max_length=80)
    predicted: list[float] = Field(min_length=2, max_length=10000)
    observed: list[float] = Field(min_length=2, max_length=10000)
    source: str = Field(min_length=1, max_length=160)


@router.post("/api/model-lab/evaluate", dependencies=[Depends(require_admin)])
async def evaluate(payload: EvaluationInput):
    import math
    if len(payload.predicted) != len(payload.observed) or not all(math.isfinite(x) for x in payload.predicted+payload.observed):
        raise HTTPException(422, "Supply matching finite prediction and observation arrays")
    n = len(payload.observed)
    errors = [p-o for p, o in zip(payload.predicted, payload.observed)]
    mean = sum(payload.observed)/n
    denom = sum((o-mean)**2 for o in payload.observed)
    result = {"model": payload.model, "variable": payload.variable, "source": payload.source, "samples": n,
              "mae": sum(abs(e) for e in errors)/n, "rmse": math.sqrt(sum(e*e for e in errors)/n),
              "r2": 1-sum(e*e for e in errors)/denom if denom else None, "timestamp": datetime.now(timezone.utc).isoformat()}
    import hashlib
    key = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    save_record("evaluation:"+key, "model_evaluation", result)
    return result
