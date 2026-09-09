import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database
from services.alert_service import classify_alerts, advisory
from services.model_service import load_models, predict, status as model_status
from services.weather_service import CITIES, current_weather, forecast

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
app = FastAPI(title="WeatherGPT", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

class RegisterBody(BaseModel):
    name: str
    email: str
    password: str
class LoginBody(BaseModel):
    email: str
    password: str
class ChatBody(BaseModel):
    message: str
    lat: float = 28.6139
    lon: float = 77.2090
    language: str = "en"
class PredictBody(BaseModel):
    kind: str
    features: list[float]

@app.on_event("startup")
def startup():
    database.init_db(); load_models()

def auth_user(request: Request):
    header = request.headers.get("authorization", "")
    token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else None
    return database.get_user_by_token(token)

PAGES = {
    "/":"index.html", "/globe":"globe.html", "/chat":"chat.html", "/dashboard":"dashboard.html",
    "/alerts":"alerts.html", "/climate":"climate.html", "/advisory":"advisory.html", "/login":"login.html", "/admin":"admin.html"
}
for route, filename in PAGES.items():
    async def page(filename=filename):
        return FileResponse(STATIC / filename)
    app.add_api_route(route, page, methods=["GET"], include_in_schema=False)

@app.get("/api/health")
def health(): return {"ok": True, "service": "WeatherGPT", "models": model_status()}
@app.get("/api/cities")
def cities(): return CITIES

@app.get("/api/weather/current")
async def current(lat: float = 28.6139, lon: float = 77.2090):
    return await current_weather(lat, lon)

@app.get("/api/weather/forecast")
async def get_forecast(lat: float = 28.6139, lon: float = 77.2090, hours: int = 24):
    return await forecast(lat, lon, max(1, min(hours, 72)))

@app.get("/api/alerts")
async def alerts(lat: float = 28.6139, lon: float = 77.2090):
    w = await current_weather(lat, lon)
    return {"weather": w, "alerts": classify_alerts(w)}

@app.get("/api/advisory")
async def get_advisory(domain: str = "public", lat: float = 28.6139, lon: float = 77.2090):
    w = await current_weather(lat, lon)
    return {"domain": domain, "weather": w, "advice": advisory(w, domain)}

@app.get("/api/climate/trend")
async def climate(lat: float = 28.6139, lon: float = 77.2090):
    w = await current_weather(lat, lon)
    base = float(w.get("temperature_2m") or 28)
    months = ["Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep"]
    temps = [round(base + x,1) for x in [-2.6,-4,-5,-4,-1,2,4.5,5.2,3.5,1.3,0.2,-1]]
    rainfall = [24,13,9,11,18,22,17,34,126,245,221,139]
    return {"source":"demo-aggregate-adapter", "months":months, "temperature":temps, "rainfall":rainfall,
            "note":"Replace this adapter with your PostgreSQL historical aggregates."}

@app.post("/api/chat")
async def chat(body: ChatBody):
    w = await current_weather(body.lat, body.lon)
    text = body.message.lower()
    if "rain" in text or "बारिश" in text:
        answer = f"Current precipitation is {w.get('precipitation',0)} mm and cloud cover is {w.get('cloud_cover','—')}%."
    elif "wind" in text or "हवा" in text:
        answer = f"Wind is {w.get('wind_speed_10m','—')} km/h from {w.get('wind_direction_10m','—')}°, with gusts {w.get('wind_gusts_10m','—')} km/h."
    elif "alert" in text or "warning" in text or "चेतावनी" in text:
        a = classify_alerts(w)[0]; answer = f"{a['type']}: {a['message']}"
    else:
        answer = (f"At your selected location it is {w.get('temperature_2m','—')}°C, humidity {w.get('relative_humidity_2m','—')}%, "
                  f"wind {w.get('wind_speed_10m','—')} km/h and pressure {w.get('pressure_msl','—')} hPa. Ask me about rain, wind, alerts or advisories.")
    return {"answer": answer, "weather": w, "engine":"local-intent-router", "language": body.language}

@app.get("/api/models/status")
def models(): return model_status()
@app.post("/api/models/predict")
def model_predict(body: PredictBody):
    if body.kind not in {"weather","disaster"}: raise HTTPException(400, "kind must be weather or disaster")
    return predict(body.kind, body.features)

@app.post("/api/auth/register")
def register(body: RegisterBody):
    if len(body.password) < 6: raise HTTPException(400, "Password must be at least 6 characters")
    user = database.create_user(body.name.strip(), body.email.strip(), body.password)
    if not user: raise HTTPException(409, "Email already registered")
    token = database.create_session(user["id"])
    return {"token":token,"user":user}

@app.post("/api/auth/login")
def login(body: LoginBody):
    user = database.authenticate(body.email, body.password)
    if not user: raise HTTPException(401, "Invalid credentials")
    token = database.create_session(user["id"])
    return {"token": token, "user": {k:user[k] for k in ("id","name","email","role","language")}}

@app.get("/api/auth/me")
def me(request: Request):
    user = auth_user(request)
    if not user: raise HTTPException(401, "Not authenticated")
    return user

@app.post("/api/auth/logout")
def logout(request: Request):
    header = request.headers.get("authorization", "")
    token = header.removeprefix("Bearer ").strip()
    if token: database.delete_session(token)
    return {"ok": True}

@app.get("/api/admin/stats")
def admin_stats(request: Request):
    user = auth_user(request)
    if not user or user["role"] != "admin": raise HTTPException(403, "Admin only")
    return {**database.stats(), "models": model_status(), "system":"healthy"}

@app.websocket("/ws/alerts")
async def alert_socket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            payload: dict[str, Any] = await ws.receive_json()
            lat = float(payload.get("lat", 28.6139)); lon = float(payload.get("lon", 77.2090))
            w = await current_weather(lat, lon)
            await ws.send_json({"type":"weather_alert_update","weather":w,"alerts":classify_alerts(w)})
    except WebSocketDisconnect:
        return
