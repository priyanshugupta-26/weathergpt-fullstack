"""Extension contracts for authoritative hazard and custom model providers."""

from typing import Protocol, Literal
from pydantic import BaseModel, Field


class TrackPoint(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timestamp: str
    kind: Literal["observed", "forecast"]


class CycloneEvent(BaseModel):
    id: str
    name: str
    source: str
    timestamp: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    track: list[TrackPoint] = []
    wind_speed_kmh: float | None = None
    pressure_hpa: float | None = None
    category: str | None = None
    movement_direction: float | None = None
    affected_region: str | None = None
    warning_status: str | None = None


class CycloneProvider(Protocol):
    async def events(self) -> list[CycloneEvent]: ...


class GridProvider(Protocol):
    async def grid(self, latitude: float, longitude: float) -> dict: ...


class AviationReportProvider(Protocol):
    async def reports(self, icao: str) -> dict: ...


# IMD, GFS, WRF and private grids implement the normalized WeatherProvider/GridProvider
# contracts. No API credentials or fabricated outputs are embedded in these adapters.
