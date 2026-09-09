import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(
    prefix="weathergpt-test-", suffix=".db"
)
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["IMD_ENABLED"] = "false"
os.environ["AI_PROVIDER"] = "deterministic"
os.environ["GROQ_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
import pytest
from fastapi.testclient import TestClient
from backend.main import app, rate_windows


@pytest.fixture
def client():
    rate_windows.clear()
    with TestClient(app) as client:
        yield client
