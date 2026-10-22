"""Compliant outbound messaging (email + SMS) routed through Go High Level.

Guard rails enforced for every send:
  * do-not-contact flag and unsubscribe list
  * SMS requires recorded sms_consent (TCPA); marketing email to clients requires email_consent
  * outreach email requires BUSINESS_ADDRESS + includes an unsubscribe link (CAN-SPAM)
  * daily cap on outreach; dry-run mode logs instead of sending
Templates must never contain clinical/PHI details.
"""
import re
import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from itsdangerous import BadSignature, URLSafeSerializer

from . import db, ghl
from .config import PRACTICE, settings

TRANSACTIONAL = ("confirmation", "reminder", "cancellation")

DEFAULT_TEMPLATES = [
    {"name": "Provider introduction", "channel": "email",
     "subject": "Collaborating on integrative care — Anavah Institute",
     "body": ("Hello {{first_name}},\n\nI'm Phillip Scherbakov, a psychiatric nurse practitioner, exercise coach and "
              "nutrition specialist at Anavah Institute in Chelsea, Manhattan. We help bridge the gap between "
              "healthcare specialists through coordinated, integrative treatment, consultation and pre-screening.\n\n"
              "I'd welcome a short call to see whether there is a good way for our practices to collaborate. "
              "You can pick a time that suits you here: {{booking_link}}\n\nWarm regards,\nPhillip Scherbakov, PMHNP\n"
              "Anavah Institute · {{phone}}")},
    {"name": "Lunch and Learn invitation", "channel": "email",
     "subject": "A Lunch and Learn for your team?",
     "body": ("Hello {{first_name}},\n\nAnavah Institute offers short educational Lunch and Learns for clinics, covering "
              "evidence-based, integrative approaches and cross-disciplinary collaboration. If this would be useful "
              "for your team, you can choose a planning time here: {{booking_link}}\n\nThank you,\nPhillip Scherbakov, PMHNP\n"
              "{{phone}}")},
    {"name": "Check-in", "channel": "email",
     "subject": "Checking in from Anavah Institute",
     "body": ("Hello {{first_name}},\n\nJust checking in from Anavah Institute. If you'd like to schedule a visit, "
              "you can find a time that works for you here: {{booking_link}}\n\nWarmly,\nAnavah Institute\n{{phone}}")},
    {"name": "Appointment reminder", "channel": "sms",
     "subject": "",
     "body": "Anavah Institute: reminder of your {{type}} on {{when}}. Manage: {{manage_link}}"},
]


def render(text: str, ctx: dict) -> str:
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: str(ctx.get(m.group(1), "")), text or "")


def base_ctx(person: dict | None = None, appt: dict | None = None) -> dict:
    from .scheduling import local_label
    ctx = {"first_name": ((person or {}).get("first_name") or (person or {}).get("name", "").split(" ")[0] or "there"),
           "booking_link": settings.site_url + "/book", "phone": PRACTICE["phone"], "practice": PRACTICE["name"]}
    if appt:
        ctx.update({"type": appt["type_name"], "when": local_label(appt["start_at"]),
                    "manage_link": f"{settings.site_url}/manage?t={appt['manage_token']}"})
    return ctx


# ---------- unsubscribe ----------
def _ser():
    return URLSafeSerializer(settings.secret_key, salt="unsub")


def unsub_token(address: str, channel: str = "email") -> str:
    return _ser().dumps({"a": address.lower(), "c": channel})


def read_unsub_token(token: str):
    try:
        d = _ser().loads(token)
        return d["a"], d["c"]
    except (BadSignature, KeyError):
        return None


def norm_addr(addr: str) -> str:
    addr = (addr or "").strip().lower()
    return addr if "@" in addr else re.sub(r"[^\d+]", "", addr)


def is_unsubscribed(conn, addr: str) -> bool:
    return conn.execute(sa.select(db.unsubscribes.c.address).where(
        db.unsubscribes.c.address == norm_addr(addr))).first() is not None


def add_unsubscribe(conn, addr: str, channel: str):
    addr = norm_addr(addr)
    if not is_unsubscribed(conn, addr):
        conn.execute(sa.insert(db.unsubscribes).values(address=addr, channel=channel))
    # also mark do-not-contact on any matching records
    for tbl in (db.clients, db.prospects):
        col = tbl.c.email if "@" in addr else tbl.c.phone
        if "@" in addr:
            conn.execute(sa.update(tbl).where(sa.func.lower(col) == addr).values(do_not_contact=True))


# ---------- sending ----------
def _sent_today(conn) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return conn.execute(sa.select(sa.func.count()).select_from(db.messages).where(
        db.messages.c.kind == "outreach", db.messages.c.status.in_(("sent", "dry_run")),
        db.messages.c.created_at >= start)).scalar() or 0


def _log(conn, **v) -> dict:
    mid = uuid.uuid4()
    conn.execute(sa.insert(db.messages).values(id=mid, **v))
    return {"id": str(mid), "status": v["status"], "error": v.get("error", "")}


def send(conn, *, channel: str, to: str, subject: str, body: str, kind: str = "outreach",
         client: dict | None = None, prospect: dict | None = None, appt: dict | None = None) -> dict:
    """Send (or dry-run) one message. Never raises for policy blocks; returns {status, error}."""
    person = client or prospect or {}
    ref = {"client_id": (client or {}).get("id"), "prospect_id": (prospect or {}).get("id"),
           "appointment_id": (appt or {}).get("id"), "channel": channel, "kind": kind, "to_address": to or "",
           "subject": subject, "body": body}

    def block(why):
        return _log(conn, status="blocked", error=why, **ref)

    if not to:
        return block(f"No {'email' if channel == 'email' else 'phone number'} on file.")
    if person.get("do_not_contact") or is_unsubscribed(conn, to):
        return block("Contact is marked do-not-contact / unsubscribed.")
    if channel == "sms" and client is not None and not client.get("sms_consent"):
        return block("No SMS consent recorded for this client.")
    if channel == "sms" and prospect is not None:
        return block("SMS to prospects is disabled (no recorded consent).")
    if kind == "outreach" and channel == "email" and client is not None and not client.get("email_consent"):
        return block("No email consent recorded for this client.")
    if kind == "outreach":
        if channel == "email" and not settings.business_address:
            return block("BUSINESS_ADDRESS is not set (required by CAN-SPAM).")
        if _sent_today(conn) >= settings.daily_cap:
            return block(f"Daily outreach cap ({settings.daily_cap}) reached.")

    html = None
    out_body = body
    if kind == "outreach":
        tok = unsub_token(to, channel)
        link = f"{settings.site_url}/unsubscribe?t={tok}"
        if channel == "email":
            out_body = f"{body}\n\n--\n{PRACTICE['name']} · {settings.business_address}\nUnsubscribe: {link}"
            esc = (body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")).replace("\n", "<br>")
            html = (f"<div style='font-family:Arial,sans-serif;font-size:15px;line-height:1.5'>{esc}"
                    f"<hr style='border:none;border-top:1px solid #ddd;margin:24px 0 8px'>"
                    f"<div style='font-size:12px;color:#777'>{PRACTICE['name']} · {settings.business_address}<br>"
                    f"<a href='{link}'>Unsubscribe</a></div></div>")
        else:
            out_body = f"{body} Reply STOP to opt out."
    ref["body"] = out_body

    if settings.dry_run:
        return _log(conn, status="dry_run", **ref)
    try:
        cid = person.get("ghl_contact_id")
        if not cid:
            cid = ghl.upsert_contact(person.get("first_name") or person.get("name", ""), person.get("last_name", ""),
                                     person.get("email"), person.get("phone"),
                                     tags=["client" if client else "prospect"])
            tbl = db.clients if client else db.prospects
            if person.get("id"):
                conn.execute(sa.update(tbl).where(tbl.c.id == person["id"]).values(ghl_contact_id=cid))
        pid = ghl.send_message(cid, channel, out_body, subject, html)
        return _log(conn, status="sent", provider_id=pid, **ref)
    except ghl.GHLError as e:
        return _log(conn, status="failed", error=str(e)[:500], **ref)


# ---------- appointment emails ----------
def notify_booking(conn, appt: dict):
    """Confirmation to the client (+ heads-up to the practice). Failures never break booking."""
    client = appt["client"]
    ctx = base_ctx(client, appt)
    subj = f"Your appointment with {PRACTICE['name']} is confirmed"
    body = (f"Hello {ctx['first_name']},\n\nYour {appt['type_name']} is confirmed for {ctx['when']} "
            f"({'telehealth' if appt['mode'] == 'telehealth' else 'in person, ' + PRACTICE['location']}).\n\n"
            f"Need to change or cancel? {ctx['manage_link']}\n\nPlease don't reply with health details by email. "
            f"Questions? Call {PRACTICE['phone']}.\n\n{PRACTICE['name']}")
    out = []
    try:
        if client.get("email"):
            out.append(send(conn, channel="email", to=client["email"], subject=subj, body=body,
                            kind="confirmation", client=client, appt=appt))
        if settings.notify_email:
            note = (f"New booking: {appt['type_name']} on {ctx['when']} — {client['first_name']} {client['last_name']} "
                    f"({client.get('email') or 'no email'}, {client.get('phone') or 'no phone'}). Source: {appt['source']}.")
            out.append(_notify_staff(conn, note))
    except Exception as e:  # never let notification problems fail a booking
        out.append({"status": "failed", "error": str(e)})
    return out


def _notify_staff(conn, text: str):
    # Internal notice: sent as a transactional message to the practice's own address (GHL contact upserted by email).
    staff = {"id": None, "name": "Anavah Staff", "first_name": "Anavah", "last_name": "Staff",
             "email": settings.notify_email}
    return send(conn, channel="email", to=settings.notify_email, subject="New booking — Anavah Institute",
                body=text, kind="confirmation", prospect=staff)
