"""Server tools called by the ElevenLabs voice agent. Auth: X-Agent-Secret header."""
from datetime import date, datetime, timedelta, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import db, messaging, scheduling as sch
from ..auth import require_agent
from ..config import PRACTICE, settings

router = APIRouter(prefix="/api/agent", dependencies=[Depends(require_agent)])


@router.get("/types")
def types():
    with db.get_engine().connect() as conn:
        return {"types": [{"slug": t["slug"], "name": t["name"], "audience": t["audience"],
                           "duration_min": t["duration_min"], "mode": t["mode"]} for t in sch.list_types(conn)]}


class AvailIn(BaseModel):
    type_slug: str
    from_date: date | None = None
    limit: int = Field(default=5, ge=1, le=10)


@router.post("/availability")
def availability(body: AvailIn):
    if settings.booking_mode != "internal":
        return {"slots": [], "booking_url": PRACTICE["booking_url"],
                "message": "Initial consultations are booked on the practice's online Google Calendar page. "
                           "Offer to open it for the caller, or take a callback request."}
    with db.get_engine().connect() as conn:
        t = sch.get_type(conn, slug=body.type_slug)
        if not t or not t["active"]:
            return {"error": "unknown_type", "message": "I couldn't find that visit type."}
        start = body.from_date or datetime.now(sch.tz()).date()
        days = sch.compute_slots(conn, t, start, start + timedelta(days=21))
    out = []
    for d in sorted(days):
        for iso in days[d]:
            if len(out) >= body.limit:
                break
            dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
            out.append({"start": iso, "spoken": sch.local_label(dt.replace(tzinfo=timezone.utc))})
        if len(out) >= body.limit:
            break
    return {"type": t["name"], "duration_min": t["duration_min"], "slots": out,
            "message": "" if out else "There are no open times in the next three weeks."}


class AgentBook(BaseModel):
    type_slug: str
    start: str
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=200)
    phone: str = ""


@router.post("/book")
def book(body: AgentBook):
    if settings.booking_mode != "internal":
        return {"booked": False, "booking_url": PRACTICE["booking_url"],
                "message": "I can't book directly. Offer to open the online scheduling page, or take a callback request."}
    if "@" not in body.email:
        return {"booked": False, "message": "That email doesn't look right. Please ask the caller to spell it again."}
    with db.get_engine().begin() as conn:
        t = sch.get_type(conn, slug=body.type_slug)
        if not t:
            return {"booked": False, "message": "I couldn't find that visit type."}
        try:
            a = sch.book(conn, type_id=t["id"], start_iso=body.start, first_name=body.first_name, last_name=body.last_name,
                         email=body.email, phone=body.phone, source="mia")
        except (sch.SlotTaken, sch.SlotInvalid) as e:
            return {"booked": False, "message": str(e)}
        messaging.notify_booking(conn, a)
    return {"booked": True, "when": sch.local_label(a["start_at"]), "type": a["type_name"],
            "message": "Booked. A confirmation email with a link to change or cancel is on its way."}


class CallbackIn(BaseModel):
    first_name: str
    last_name: str = ""
    phone: str = ""
    email: str = ""
    reason: str = Field(default="", max_length=200)


@router.post("/callback")
def callback(body: CallbackIn):
    if not (body.phone or body.email):
        return {"ok": False, "message": "I need a phone number or email so the office can reach you."}
    with db.get_engine().begin() as conn:
        c = sch.upsert_client(conn, body.first_name, body.last_name, body.email, body.phone, False, "mia")
        conn.execute(sa.insert(db.client_notes).values(client_id=c["id"], created_by="mia",
                                                       body=f"Callback requested via Mia. {body.reason}".strip()))
        if settings.notify_email:
            messaging._notify_staff(conn, f"Callback requested via Mia: {body.first_name} {body.last_name}, "
                                          f"{body.phone or 'no phone'}, {body.email or 'no email'}. {body.reason}")
    return {"ok": True, "message": "The office will follow up soon."}
