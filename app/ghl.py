"""Go High Level (LeadConnector) client using a Private Integration Token.

NOTE: Endpoint paths/Version headers below follow GHL's public API v2 docs as of writing.
Confirm them against https://marketplace.gohighlevel.com/docs once your token is created
(use Settings > "Test GHL connection" in the admin dashboard).
"""
import httpx

from .config import settings

BASE = "https://services.leadconnectorhq.com"


class GHLError(Exception):
    pass


def configured() -> bool:
    return bool(settings.ghl_token and settings.ghl_location_id)


def _headers(version: str) -> dict:
    return {"Authorization": f"Bearer {settings.ghl_token}", "Version": version,
            "Content-Type": "application/json", "Accept": "application/json"}


def _call(method: str, path: str, version: str, json=None, params=None) -> dict:
    if not configured():
        raise GHLError("GHL is not configured (GHL_TOKEN / GHL_LOCATION_ID).")
    try:
        r = httpx.request(method, BASE + path, headers=_headers(version), json=json, params=params, timeout=20)
    except httpx.HTTPError as e:
        raise GHLError(f"GHL network error: {e}")
    if r.status_code >= 400:
        raise GHLError(f"GHL {r.status_code}: {r.text[:300]}")
    return r.json() if r.content else {}


def upsert_contact(first_name="", last_name="", email=None, phone=None, tags=None, source="Anavah Platform") -> str:
    body = {"locationId": settings.ghl_location_id, "firstName": first_name, "lastName": last_name,
            "source": source, "tags": tags or []}
    if email:
        body["email"] = email
    if phone:
        body["phone"] = phone
    data = _call("POST", "/contacts/upsert", "2021-07-28", json=body)
    cid = (data.get("contact") or {}).get("id") or data.get("id")
    if not cid:
        raise GHLError("GHL did not return a contact id.")
    return cid


def send_message(contact_id: str, channel: str, body: str, subject: str = "", html: str | None = None) -> str:
    payload = {"contactId": contact_id}
    if channel == "email":
        payload.update({"type": "Email", "subject": subject, "html": html or body.replace("\n", "<br>")})
    else:
        payload.update({"type": "SMS", "message": body})
    data = _call("POST", "/conversations/messages", "2021-04-15", json=payload)
    return data.get("messageId") or data.get("id") or ""


def test_connection() -> dict:
    data = _call("GET", f"/locations/{settings.ghl_location_id}", "2021-07-28")
    loc = data.get("location") or data
    return {"ok": True, "location": loc.get("name", "")}
