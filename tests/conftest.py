import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "ANTHROPIC_API_KEY", "GHL_TOKEN", "GHL_LOCATION_ID", "ELEVENLABS_AGENT_ID"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DEV_ADMIN_TOKEN", "devtok")
    monkeypatch.setenv("AGENT_WEBHOOK_SECRET", "agentsecret")
    monkeypatch.setenv("OUTREACH_DRY_RUN", "true")
    monkeypatch.setenv("BUSINESS_ADDRESS", "123 W 23rd St, New York, NY 10011")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("TIMEZONE", "America/New_York")
    monkeypatch.setenv("BOOKING_MODE", "internal")  # the legacy internal calendar is what these tests cover
    from app import db, util
    db.reset_engine()
    util.clear_limits()
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c
    db.reset_engine()


@pytest.fixture()
def admin(client):
    return {"Authorization": "Bearer devtok"}


@pytest.fixture()
def agent_h():
    return {"X-Agent-Secret": "agentsecret"}
