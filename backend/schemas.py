import math
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Coordinates(BaseModel):
    latitude: float = Field(25.5941, ge=-90, le=90)
    longitude: float = Field(85.1376, ge=-180, le=180)
    name: str = Field("Patna", max_length=160)


class Credentials(BaseModel):
    email: str = Field(
        min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    password: str = Field(min_length=10, max_length=128)
    name: str = Field("Explorer", min_length=1, max_length=100)


class ChatRequest(Coordinates):
    message: str = Field(min_length=1, max_length=2000)
    language: Literal["en", "hi"] = "en"
    conversation: str = Field("default", max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


class PredictionRequest(BaseModel):
    features: dict[str, float] | list[float] = Field(default_factory=dict)

    @field_validator("features")
    @classmethod
    def finite(cls, value):
        if isinstance(value, dict):
            if any(not math.isfinite(v) for v in value.values()):
                raise ValueError("All features must be finite numbers")
        elif isinstance(value, list):
            if any(not math.isfinite(v) for v in value):
                raise ValueError("All features must be finite numbers")
        return value


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    language: Literal["en", "hi"] = "en"
    theme: Literal["dark", "light", "system"] = "dark"
    units: Literal["metric"] = "metric"
    default_location: Coordinates | None = None
    notifications: dict[str, bool] = Field(default_factory=dict, max_length=12)


class SavedLocationInput(Coordinates):
    district: str = Field("", max_length=100)
    state: str = Field("", max_length=100)
    radius_km: float = Field(25, ge=0, le=250)
    label: Literal["Home", "College", "Work", "Family", "Farm", "Custom"] = "Custom"
