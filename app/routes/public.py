from datetime import date, datetime, timedelta, timezone

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, EmailStr, Field

from .. import db, ics, kb, messaging, scheduling as sch
from ..config import PRACTICE, settings
from ..util import rate_limit

def _internal_booking_only():
    """Public booking/manage endpoints are live only when BOOKING_MODE=internal (default is Google Calendar)."""
    if settings.booking_mode != "internal":
        raise HTTPException(status_code=410, detail="Online booking is handled through our Google Calendar page.")


router = APIRouter()


def _appt_out(a: dict) -> dict:
    return {"id": str(a["id"]), "type": a["type_name"], "start_at": a["start_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_at": a["end_at"].strftime("%Y-%m-%dT%H:%M:%SZ"), "when": sch.local_label(a["start_at"]),
            "mode": a["mode"], "status": a["status"], "token": a["manage_token"],
            "manage_url": f"{settings.site_url}/manage?t={a['manage_token']}",
            "ics_url": f"/api/public/ics?t={a['manage_token']}"}


@router.get("/api/public/config")
def public_config():
    if settings.booking_mode != "internal":
        return {"practice": PRACTICE, "booking_mode": "google", "booking_url": PRACTICE["booking_url"], "types": []}
    with db.get_engine().connect() as conn:
        types = sch.list_types(conn)
        cfg = sch.booking_settings(conn)
    return {"practice": PRACTICE, "booking_mode": "internal", "timezone": settings.timezone, "booking": cfg,
            "types": [{"id": str(t["id"]), "slug": t["slug"], "name": t["name"], "audience": t["audience"],
                       "duration_min": t["duration_min"], "mode": t["mode"], "description": t["description"]}
                      for t in types]}


@router.get("/api/public/slots", dependencies=[Depends(_internal_booking_only)])
def slots(type: str, start: date | None = None, days: int = 14):
    days = max(1, min(days, 31))
    start = start or datetime.now(sch.tz()).date()
    with db.get_engine().connect() as conn:
        t = sch.get_type(conn, slug=type) or (sch.get_type(conn, type_id=type) if len(type) == 36 else None)
        if not t or not t["active"]:
            raise HTTPException(404, "Unknown appointment type.")
        data = sch.compute_slots(conn, t, start, start + timedelta(days=days - 1))
    return {"type": t["slug"], "duration_min": t["duration_min"], "timezone": settings.timezone, "days": data}


class BookIn(BaseModel):
    type: str
    start: str
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    phone: str = Field(default="", max_length=40)
    mode: str = "telehealth"
    message: str = Field(default="", max_length=1000)
    sms_consent: bool = False
    ack: bool = False
    website: str = ""  # honeypot


@router.post("/api/public/book", dependencies=[Depends(_internal_booking_only)])
def book(body: BookIn, request: Request):
    rate_limit(request, "book", 8, 3600)
    if body.website:  # bots fill the hidden field; pretend success
        return {"ok": True}
    if not body.ack:
        raise HTTPException(422, "Please confirm you understand this is not for emergencies.")
    with db.get_engine().begin() as conn:
        t = sch.get_type(conn, slug=body.type) or (sch.get_type(conn, type_id=body.type) if len(body.type) == 36 else None)
        if not t:
            raise HTTPException(404, "Unknown appointment type.")
        try:
            appt = sch.book(conn, type_id=t["id"], start_iso=body.start, first_name=body.first_name,
                            last_name=body.last_name, email=body.email, phone=body.phone, mode=body.mode,
                            message=body.message, sms_consent=body.sms_consent and bool(body.phone), source="web")
        except sch.SlotTaken as e:
            raise HTTPException(409, str(e))
        except sch.SlotInvalid as e:
            raise HTTPException(422, str(e))
        messaging.notify_booking(conn, appt)
    return {"ok": True, "appointment": _appt_out(appt)}


def _by_token(conn, token):
    a = sch.get_by_token(conn, token)
    if not a:
        raise HTTPException(404, "Appointment not found.")
    return a


@router.get("/api/public/appointment", dependencies=[Depends(_internal_booking_only)])
def get_appt(t: str):
    with db.get_engine().connect() as conn:
        a = _by_token(conn, t)
        return {**_appt_out(a), "first_name": a["client"]["first_name"], "type_slug": (sch.get_type(conn, type_id=a["type_id"]) or {}).get("slug")}


@router.post("/api/public/appointment/cancel", dependencies=[Depends(_internal_booking_only)])
def cancel_appt(t: str, request: Request):
    rate_limit(request, "manage", 20, 3600)
    with db.get_engine().begin() as conn:
        a = _by_token(conn, t)
        if a["status"] in ("pending", "confirmed"):
            sch.cancel(conn, a["id"])
            c = a["client"]
            if c.get("email"):
                messaging.send(conn, channel="email", to=c["email"], subject="Your appointment was cancelled",
                               body=f"Hello {c['first_name']},\n\nYour {a['type_name']} on {sch.local_label(a['start_at'])} "
                                    f"has been cancelled. You can book a new time any time at {settings.site_url}/book.\n\n{PRACTICE['name']}",
                               kind="cancellation", client=c, appt=a)
    return {"ok": True}


class RescheduleIn(BaseModel):
    start: str


@router.post("/api/public/appointment/reschedule", dependencies=[Depends(_internal_booking_only)])
def reschedule_appt(t: str, body: RescheduleIn, request: Request):
    rate_limit(request, "manage", 20, 3600)
    with db.get_engine().begin() as conn:
        a = _by_token(conn, t)
        if a["status"] not in ("pending", "confirmed"):
            raise HTTPException(409, "This appointment can't be changed.")
        try:
            new = sch.reschedule(conn, a, body.start)
        except sch.SlotTaken as e:
            raise HTTPException(409, str(e))
        c = new["client"]
        if c.get("email"):
            messaging.send(conn, channel="email", to=c["email"], subject="Your appointment was rescheduled",
                           body=f"Hello {c['first_name']},\n\nYour {new['type_name']} is now {sch.local_label(new['start_at'])}.\n"
                                f"Manage: {settings.site_url}/manage?t={new['manage_token']}\n\n{PRACTICE['name']}",
                           kind="confirmation", client=c, appt=new)
    return {"ok": True, "appointment": _appt_out(new)}


@router.get("/api/public/ics", dependencies=[Depends(_internal_booking_only)])
def ics_file(t: str):
    with db.get_engine().connect() as conn:
        a = _by_token(conn, t)
    return Response(ics.appointment_ics(a), media_type="text/calendar",
                    headers={"Content-Disposition": 'attachment; filename="anavah-appointment.ics"'})


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field(default="", max_length=40)
    message: str = Field(default="", max_length=1500)
    website: str = ""


@router.post("/api/public/contact")
def contact(body: ContactIn, request: Request):
    rate_limit(request, "contact", 5, 3600)
    if body.website:
        return {"ok": True}
    parts = body.name.strip().split(" ", 1)
    with db.get_engine().begin() as conn:
        c = sch.upsert_client(conn, parts[0], parts[1] if len(parts) > 1 else "", body.email, body.phone, False, "contact_form")
        if body.message.strip():
            conn.execute(sa.insert(db.client_notes).values(client_id=c["id"], body="Contact form: " + body.message.strip(),
                                                           created_by="contact_form"))
        if settings.notify_email:
            messaging._notify_staff(conn, f"New contact form message from {body.name} ({body.email}, {body.phone or 'no phone'}):\n\n{body.message}")
    return {"ok": True}


class ChatIn(BaseModel):
    messages: list[dict] = Field(max_length=40)


@router.post("/api/chat")
def chat(body: ChatIn, request: Request):
    rate_limit(request, "chat", 40, 3600)
    return kb.chat(body.messages)


@router.get("/api/voice/session")
def voice_session(request: Request):
    """Gives the browser what it needs to start an ElevenLabs agent conversation."""
    rate_limit(request, "voice", 10, 3600)
    if not settings.eleven_agent_id:
        return {"enabled": False}
    if not settings.eleven_key:  # public agent: browser connects with agentId
        return {"enabled": True, "agentId": settings.eleven_agent_id}
    try:
        r = httpx.get("https://api.elevenlabs.io/v1/convai/conversation/get-signed-url",
                      params={"agent_id": settings.eleven_agent_id}, headers={"xi-api-key": settings.eleven_key}, timeout=15)
        r.raise_for_status()
        return {"enabled": True, "signedUrl": r.json()["signed_url"]}
    except (httpx.HTTPError, KeyError, ValueError):
        return {"enabled": False}


_UNSUB_PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Unsubscribe — Anavah Institute</title><body style="font-family:Georgia,serif;background:#f6f3ec;color:#14213d;display:grid;place-items:center;min-height:100vh;margin:0">
<div style="max-width:440px;padding:32px;text-align:center"><h1 style="font-weight:500">{h}</h1><p style="font-family:Arial,sans-serif;color:#555">{p}</p>{form}</div>"""


@router.get("/unsubscribe", response_class=HTMLResponse)
def unsub_page(t: str):
    parsed = messaging.read_unsub_token(t)
    if not parsed:
        return _UNSUB_PAGE.format(h="Link not valid", p="This unsubscribe link is invalid or expired. Email Scherb@anavah-Institute.org and we'll remove you.", form="")
    addr, _ = parsed
    form = f'<form method=post action="/unsubscribe?t={t}"><button style="padding:12px 24px;background:#14213d;color:#fff;border:0;border-radius:6px;font-size:16px;cursor:pointer">Unsubscribe {addr}</button></form>'
    return _UNSUB_PAGE.format(h="Unsubscribe", p="Confirm to stop receiving messages from Anavah Institute.", form=form)


@router.post("/unsubscribe", response_class=HTMLResponse)
def unsub_do(t: str):
    parsed = messaging.read_unsub_token(t)
    if not parsed:
        raise HTTPException(400, "Invalid link.")
    with db.get_engine().begin() as conn:
        messaging.add_unsubscribe(conn, parsed[0], parsed[1])
    return _UNSUB_PAGE.format(h="You're unsubscribed", p="You won't receive further messages from us.", form="")
