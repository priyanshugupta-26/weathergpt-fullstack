import math
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Coordinates(BaseModel):
    latitude: float = Field(25.5941, ge=-90, le=90)
    longitude: float = Field(85.1376, ge=-180, le=180)
    name: str = Field("Patna", max_length=160)


SUPPORTED_LANGUAGES = (
    "en", "hi", "as", "bn", "brx", "doi", "gu", "kn", "ks",
    "kok", "mai", "ml", "mni", "mr", "ne", "or", "pa", "sa",
    "sat", "sd", "ta", "te", "ur"
)


class Credentials(BaseModel):
    email: str | None = Field(default=None, max_length=254)
    mobile: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field("Explorer", min_length=1, max_length=100)


class RegisterInput(BaseModel):
    email: str = Field(
        min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str | None = Field(default=None, max_length=128)
    name: str | None = Field(default=None, max_length=100)
    full_name: str | None = Field(default=None, max_length=100)
    mobile: str | None = Field(default=None, max_length=30)
    mobile_number: str | None = Field(default=None, max_length=30)
    state: str | None = Field(default="", max_length=100)
    district: str | None = Field(default="", max_length=100)
    city: str | None = Field(default="", max_length=100)
    preferred_language: str = Field(default="en", max_length=20)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class LoginInput(BaseModel):
    email: str | None = Field(default=None, max_length=254)
    mobile: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=1, max_length=128)


class ChatRequest(Coordinates):
    message: str = Field(min_length=1, max_length=2000)
    language: str = Field("en", max_length=20)
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
    name: str | None = Field(default=None, min_length=1, max_length=100)
    mobile: str | None = Field(default=None, max_length=30)
    language: str | None = Field(default=None, max_length=20)
    preferred_language: str | None = Field(default=None, max_length=20)
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    theme: Literal["dark", "light", "system"] | None = None
    units: Literal["metric"] | None = None
    default_location: Coordinates | None = None
    notifications: dict[str, bool] | None = None
    preferences: dict | None = None


class SavedLocationInput(Coordinates):
    district: str = Field("", max_length=100)
    state: str = Field("", max_length=100)
    radius_km: float = Field(25, ge=0, le=250)
    label: Literal["Home", "College", "Work", "Family", "Farm", "Custom"] = "Custom"
