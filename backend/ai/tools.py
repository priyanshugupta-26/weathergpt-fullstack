"""Whitelisted, validated weather tools. No arbitrary model-directed execution."""
from datetime import date, timedelta
from pydantic import BaseModel, Field, ConfigDict, model_validator
from ..providers.engine import weather_engine
from ..providers.weather import earthquakes
from ..providers.imd import imd
from ..services.alerts import alerts_service


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start: date | None = None
    end: date | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.start or self.end:
            if not self.start or not self.end or self.end < self.start or (self.end-self.start).days > 730 or self.start < date(1940,1,1) or self.end > date.today()-timedelta(days=5):
                raise ValueError("Invalid archive range")
        return self


class WeatherToolRouter:
    names = {"get_current_weather", "get_forecast", "get_air_quality", "get_earthquake_data",
             "get_climate_history", "get_marine", "get_active_disaster_alerts",
             "get_imd_current_weather", "get_imd_warning", "get_imd_nowcast",
             "get_imd_city_forecast", "get_imd_rainfall", "get_imd_cyclone_data",
             "get_imd_marine_warning", "get_imd_agromet"}

    async def call(self, name, arguments):
        if name not in self.names:
            raise ValueError("Tool is not allowed")
        args = ToolArguments.model_validate(arguments)
        lat, lon = args.latitude, args.longitude
        if name in ("get_current_weather", "get_forecast"):
            return await weather_engine.weather(lat, lon)
        if name == "get_air_quality":
            return await weather_engine.air(lat, lon)
        if name == "get_marine":
            return await weather_engine.marine(lat, lon)
        if name == "get_earthquake_data":
            return await earthquakes()
        if name == "get_climate_history":
            if not args.start or not args.end:
                return {"status": "needs_dates", "message": "Supply explicit start and end dates"}
            return await weather_engine.history(lat, lon, args.start.isoformat(), args.end.isoformat())
        if name == "get_active_disaster_alerts":
            weather = await weather_engine.weather(lat, lon)
            return {"alerts": alerts_service.evaluate(weather), "source": "WeatherGPT threshold screening"}
        product = {"get_imd_current_weather": "current", "get_imd_warning": "warnings",
                   "get_imd_nowcast": "nowcast", "get_imd_city_forecast": "forecast",
                   "get_imd_rainfall": "rainfall", "get_imd_cyclone_data": "cyclone",
                   "get_imd_marine_warning": "marine", "get_imd_agromet": "agromet"}[name]
        return await imd.fetch(product)


tools = WeatherToolRouter()
