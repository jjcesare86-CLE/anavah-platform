"""Environment-driven configuration. Everything secret comes from env vars (Render dashboard)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """Read lazily so tests can monkeypatch os.environ before use."""

    @property
    def site_url(self): return _env("SITE_URL", "http://localhost:8000").rstrip("/")
    @property
    def timezone(self): return _env("TIMEZONE", "America/New_York")
    @property
    def secret_key(self): return _env("SECRET_KEY", "dev-secret-change-me")
    @property
    def database_url(self): return _env("DATABASE_URL", f"sqlite:///{ROOT / 'dev.db'}")
    @property
    def supabase_url(self): return _env("SUPABASE_URL").rstrip("/")
    @property
    def supabase_anon_key(self): return _env("SUPABASE_ANON_KEY")
    @property
    def admin_emails(self): return {e.strip().lower() for e in _env("ADMIN_EMAILS").split(",") if e.strip()}
    @property
    def dev_admin_token(self): return _env("DEV_ADMIN_TOKEN")
    @property
    def anthropic_key(self): return _env("ANTHROPIC_API_KEY")
    @property
    def anthropic_model(self): return _env("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    @property
    def eleven_key(self): return _env("ELEVENLABS_API_KEY")
    @property
    def eleven_agent_id(self): return _env("ELEVENLABS_AGENT_ID")
    @property
    def agent_secret(self): return _env("AGENT_WEBHOOK_SECRET")
    @property
    def ghl_token(self): return _env("GHL_TOKEN")
    @property
    def ghl_location_id(self): return _env("GHL_LOCATION_ID")
    @property
    def notify_email(self): return _env("NOTIFY_EMAIL")
    @property
    def business_address(self): return _env("BUSINESS_ADDRESS")
    @property
    def booking_mode(self):
        """'google' (default): all scheduling goes through the Google Calendar booking page.
        'internal': the built-in calendar (Supabase) is live. Kept dormant in case it is wanted later."""
        return _env("BOOKING_MODE", "google").lower()
    @property
    def dry_run(self): return _bool("OUTREACH_DRY_RUN", True)
    @property
    def daily_cap(self): return int(_env("OUTREACH_DAILY_CAP", "40") or 40)


settings = Settings()

# Public practice facts (shown on site, in emails, and given to Mia). Single source: config/practice.json
import json as _json

PRACTICE = _json.loads((ROOT / "config" / "practice.json").read_text(encoding="utf-8"))
