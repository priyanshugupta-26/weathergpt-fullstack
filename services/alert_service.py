def classify_alerts(weather: dict):
    alerts = []
    wind = float(weather.get("wind_gusts_10m") or 0)
    rain = float(weather.get("precipitation") or 0)
    temp = float(weather.get("temperature_2m") or 0)
    if wind >= 75:
        alerts.append({"type":"Severe Wind","severity":"high","message":f"Wind gusts near {wind:.0f} km/h. Avoid exposed areas."})
    elif wind >= 50:
        alerts.append({"type":"Strong Wind","severity":"moderate","message":f"Wind gusts near {wind:.0f} km/h. Secure loose outdoor objects."})
    if rain >= 20:
        alerts.append({"type":"Heavy Rain","severity":"high","message":f"Heavy precipitation detected ({rain:.1f} mm). Watch low-lying areas."})
    elif rain >= 8:
        alerts.append({"type":"Rain Advisory","severity":"moderate","message":f"Significant rain detected ({rain:.1f} mm). Carry rain protection."})
    if temp >= 42:
        alerts.append({"type":"Heat Alert","severity":"high","message":f"Very high temperature ({temp:.1f}°C). Limit midday exposure."})
    if not alerts:
        alerts.append({"type":"No Severe Hazard","severity":"low","message":"No severe threshold crossed in the current live observation."})
    return alerts

def advisory(weather: dict, domain: str):
    rain = float(weather.get("precipitation") or 0)
    wind = float(weather.get("wind_speed_10m") or 0)
    temp = float(weather.get("temperature_2m") or 0)
    domain = domain.lower()
    if domain == "agriculture":
        return [
            "Delay pesticide spraying if rain or strong wind is expected.",
            "Prefer irrigation during cooler hours when heat is high.",
            f"Current signal: {temp:.1f}°C, rain {rain:.1f} mm, wind {wind:.1f} km/h."
        ]
    if domain == "aviation":
        return ["Review cross-wind limits before dispatch.", "Check official METAR/TAF before operational decisions.", f"Surface wind signal: {wind:.1f} km/h."]
    if domain == "marine":
        return ["Small craft should reassess departure when winds strengthen.", "Use official marine warnings for navigation.", f"Current wind signal: {wind:.1f} km/h."]
    return ["Carry water in high heat.", "Avoid flooded roads during intense rain.", f"Current local signal: {temp:.1f}°C, wind {wind:.1f} km/h."]
