"""Admin auth: Supabase Auth (email+password) verified server-side, restricted to ADMIN_EMAILS."""
import hmac
import time

import httpx
from fastapi import HTTPException, Request

from .config import settings

_cache: dict[str, tuple[float, str]] = {}


def login(email: str, password: str) -> dict:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(503, "Supabase Auth is not configured.")
    if email.strip().lower() not in settings.admin_emails:
        raise HTTPException(401, "Invalid credentials.")
    try:
        r = httpx.post(f"{settings.supabase_url}/auth/v1/token", params={"grant_type": "password"},
                       headers={"apikey": settings.supabase_anon_key},
                       json={"email": email.strip(), "password": password}, timeout=15)
    except httpx.HTTPError:
        raise HTTPException(502, "Could not reach the login service.")
    if r.status_code != 200:
        raise HTTPException(401, "Invalid credentials.")
    d = r.json()
    return {"access_token": d["access_token"], "expires_in": d.get("expires_in", 3600), "email": email.strip().lower()}


def _verify(token: str) -> str | None:
    now = time.time()
    hit = _cache.get(token)
    if hit and hit[0] > now:
        return hit[1]
    if settings.dev_admin_token and not settings.supabase_url:
        return "dev@local" if hmac.compare_digest(token, settings.dev_admin_token) else None
    if not settings.supabase_url:
        return None
    try:
        r = httpx.get(f"{settings.supabase_url}/auth/v1/user",
                      headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"}, timeout=10)
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    email = (r.json().get("email") or "").lower()
    if email not in settings.admin_emails:
        return None
    _cache[token] = (now + 60, email)
    if len(_cache) > 200:
        _cache.clear()
    return email


def require_admin(request: Request) -> str:
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "):
        raise HTTPException(401, "Not signed in.")
    email = _verify(h[7:].strip())
    if not email:
        raise HTTPException(401, "Session expired. Please sign in again.")
    return email


def require_agent(request: Request):
    secret = settings.agent_secret
    got = request.headers.get("x-agent-secret", "")
    if not secret or not hmac.compare_digest(got, secret):
        raise HTTPException(401, "Unauthorized.")
