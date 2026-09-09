"""Read-only HTTP smoke checks against a running local server."""

import json
import urllib.request
from datetime import date, timedelta

BASE = "http://127.0.0.1:8000"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=45) as r:
        data = r.read()
        return r.status, json.loads(data) if "application/json" in r.headers.get(
            "content-type", ""
        ) else data


for path in [
    "/api/health",
    "/api/weather/forecast",
    "/api/globe/grid",
    "/api/earthquakes",
    "/api/weather/air-quality",
    "/api/weather/marine?latitude=18.6&longitude=72.5",
    "/api/locations/search?q=Mumbai",
    "/api/weather/history?start="
    + str(date.today() - timedelta(days=40))
    + "&end="
    + str(date.today() - timedelta(days=10)),
    "/api/providers/status",
]:
    status, d = get(path)
    print(
        path,
        status,
        {k: d[k] for k in ["status", "source", "message"] if k in d},
        "items",
        len(
            d.get(
                "daily",
                d.get("events", d.get("cells", d.get("results", d.get("hourly", [])))),
            )
        ),
    )
for path in [
    "/",
    "/globe",
    "/forecast",
    "/chat",
    "/alerts",
    "/climate",
    "/agriculture",
    "/aviation",
    "/marine",
    "/dashboard",
    "/profile",
    "/settings",
    "/admin",
    "/icon.svg",
    "/manifest.webmanifest",
]:
    print(path, get(path)[0])
