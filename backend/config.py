from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", ROOT / ".env.local"), extra="ignore")
    app_env: Literal["development", "production", "test"] = "development"
    ai_provider: Literal["auto", "groq", "gemini", "deterministic"] = "auto"
    ai_primary_provider: Literal["groq", "gemini"] = "groq"
    ai_fallback_provider: Literal["groq", "gemini"] = "gemini"
    ai_timeout: float = 20
    groq_api_key: str = ""
    groq_model: str = ""
    gemini_api_key: str = ""
    gemini_model: str = ""
    imd_base_url: str = "https://api.imd.gov.in"
    imd_token: str = ""
    imd_auth_header: str = "Authorization"
    imd_auth_scheme: str = "Bearer"
    imd_enabled: bool = True
    imd_refresh_seconds: int = 300
    cap_feed_url: str = ""
    wrf_data_path: str = ""
    database_url: str = "sqlite:///./data/weathergpt.db"
    scheduler_enabled: bool = True
    refresh_seconds: int = 600
    provider_timeout: float = 12
    session_days: int = 7
    secure_cookies: bool = False
    development_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    trusted_models: bool = False
    admin_email: str = ""
    admin_password: str = ""
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4.1-mini"


settings = Settings()
(ROOT / "data").mkdir(exist_ok=True)
