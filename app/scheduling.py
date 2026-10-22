"""Availability + booking engine.

- Weekly availability rules are wall-clock times in the practice timezone.
- Everything is stored in UTC; slot arithmetic is done in UTC so DST changes can't skew durations.
- Single-practitioner calendar: any live (pending/confirmed) appointment blocks every type.
"""
import secrets
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from . import db
from .config import settings

LIVE = ("pending", "confirmed")

DEFAULT_BOOKING = {"min_notice_hours": 12, "max_advance_days": 60, "slot_step_min": 30}

# Starter appointment types taken from the Anavah site copy. Durations are PLACEHOLDERS for Phillip to set in Settings.
DEFAULT_TYPES = [
    ("Psychiatric Intake", "psychiatric-intake", "patient", 60, 10, "New patient psychiatric evaluation."),
    ("Psychiatric Follow-Up", "psychiatric-follow-up", "patient", 30, 5, "Follow-up for existing patients."),
    ("Blood Work Analysis", "blood-work-analysis", "patient", 30, 5, "Review of lab results through an integrative lens."),
    ("Functional Fitness Assessment", "functional-fitness-assessment", "patient", 45, 10, "Movement and exercise readiness assessment."),
    ("Nutrition Optimization", "nutrition-optimization", "patient", 45, 5, "Nutrition consultation."),
    ("Provider Consultation Call", "provider-consultation", "provider", 30, 5, "Case-based collaboration call for healthcare providers."),
    ("Lunch and Learn Planning", "lunch-and-learn", "provider", 30, 5, "Plan an educational session at your clinic."),
    ("Networking Call", "networking-call", "provider", 20, 5, "Intro call for referral partners and organizations."),
]
DEFAULT_RULES = [(d, "09:00", "17:00") for d in range(5)]  # Mon-Fri placeholder; Phillip sets real hours


class SlotTaken(Exception):
    pass


class SlotInvalid(Exception):
    pass


def tz() -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------- settings / seed ----------
def get_setting(conn, key: str, default):
    r = conn.execute(sa.select(db.settings_table.c.value).where(db.settings_table.c.key == key)).first()
    return r[0] if r else default


def put_setting(conn, key: str, value):
    exists = conn.execute(sa.select(db.settings_table.c.key).where(db.settings_table.c.key == key)).first()
    if exists:
        conn.execute(sa.update(db.settings_table).where(db.settings_table.c.key == key).values(value=value))
    else:
        conn.execute(sa.insert(db.settings_table).values(key=key, value=value))


def booking_settings(conn) -> dict:
    return {**DEFAULT_BOOKING, **(get_setting(conn, "booking", {}) or {})}


def seed_defaults(conn):
    if conn.execute(sa.select(sa.func.count()).select_from(db.appointment_types)).scalar() == 0:
        for i, (name, slug, aud, dur, buf, desc) in enumerate(DEFAULT_TYPES):
            conn.execute(sa.insert(db.appointment_types).values(
                name=name, slug=slug, audience=aud, duration_min=dur, buffer_after_min=buf,
                description=desc, mode="either", active=True, sort=i))
    if conn.execute(sa.select(sa.func.count()).select_from(db.availability_rules)).scalar() == 0:
        for wd, s, e in DEFAULT_RULES:
            conn.execute(sa.insert(db.availability_rules).values(weekday=wd, start_time=s, end_time=e, active=True))
    if conn.execute(sa.select(sa.func.count()).select_from(db.templates)).scalar() == 0:
        from .messaging import DEFAULT_TEMPLATES
        for t in DEFAULT_TEMPLATES:
            conn.execute(sa.insert(db.templates).values(**t))


# ---------- queries ----------
def list_types(conn, audience=None, active_only=True):
    q = sa.select(db.appointment_types).order_by(db.appointment_types.c.sort, db.appointment_types.c.name)
    if active_only:
        q = q.where(db.appointment_types.c.active.is_(True))
    if audience:
        q = q.where(db.appointment_types.c.audience == audience)
    return [db.row(r) for r in conn.execute(q)]


def get_type(conn, type_id=None, slug=None):
    t = db.appointment_types
    q = sa.select(t)
    q = q.where(t.c.id == type_id) if type_id else q.where(t.c.slug == slug)
    r = conn.execute(q).first()
    return db.row(r) if r else None


def _hm(s: str) -> time:
    h, m = s.split(":")[:2]
    return time(int(h), int(m))


def _busy(conn, start: datetime, end: datetime):
    a = db.appointments
    appts = conn.execute(sa.select(a.c.start_at, a.c.blocked_until).where(
        a.c.status.in_(LIVE), a.c.start_at < end, a.c.blocked_until > start)).all()
    off = conn.execute(sa.select(db.time_off.c.start_at, db.time_off.c.end_at).where(
        db.time_off.c.start_at < end, db.time_off.c.end_at > start)).all()
    return [(db.utc(s), db.utc(e)) for s, e in list(appts) + list(off)]


def compute_slots(conn, appt_type: dict, d_from: date, d_to: date, now: datetime | None = None) -> dict[str, list[str]]:
    """Return {'YYYY-MM-DD' (local date): [UTC ISO start, ...]} for bookable starts."""
    now = now or now_utc()
    cfg = booking_settings(conn)
    zone = tz()
    earliest = now + timedelta(hours=cfg["min_notice_hours"])
    latest = now + timedelta(days=cfg["max_advance_days"])
    dur = timedelta(minutes=appt_type["duration_min"])
    buf = timedelta(minutes=appt_type["buffer_after_min"])
    step = timedelta(minutes=max(5, int(cfg["slot_step_min"])))

    rules = conn.execute(sa.select(db.availability_rules).where(db.availability_rules.c.active.is_(True))).all()
    by_wd: dict[int, list] = {}
    for r in rules:
        by_wd.setdefault(r.weekday, []).append((_hm(r.start_time), _hm(r.end_time)))

    win_start = datetime.combine(d_from, time(0), tzinfo=zone).astimezone(timezone.utc) - timedelta(hours=1)
    win_end = datetime.combine(d_to + timedelta(days=1), time(0), tzinfo=zone).astimezone(timezone.utc) + timedelta(days=1)
    busy = _busy(conn, win_start, win_end)

    out: dict[str, list[str]] = {}
    day = d_from
    while day <= d_to:
        slots = []
        for s_t, e_t in sorted(by_wd.get(day.weekday(), [])):
            w_start = datetime.combine(day, s_t, tzinfo=zone).astimezone(timezone.utc)
            w_end = datetime.combine(day, e_t, tzinfo=zone).astimezone(timezone.utc)
            cur = w_start
            while cur + dur <= w_end:
                blocked_end = cur + dur + buf
                ok = cur >= earliest and cur <= latest
                if ok:
                    for b_s, b_e in busy:
                        if cur < b_e and blocked_end > b_s:
                            ok = False
                            break
                if ok:
                    slots.append(cur.strftime("%Y-%m-%dT%H:%M:%SZ"))
                cur += step
        if slots:
            out[day.isoformat()] = sorted(set(slots))
        day += timedelta(days=1)
    return out


def local_label(dt: datetime) -> str:
    l = db.utc(dt).astimezone(tz())
    return l.strftime("%A, %B %-d at %-I:%M %p %Z")


# ---------- clients ----------
def upsert_client(conn, first_name, last_name, email, phone, sms_consent=False, source="web") -> dict:
    c = db.clients
    email = (email or "").strip()
    existing = None
    if email:
        existing = conn.execute(sa.select(c).where(sa.func.lower(c.c.email) == email.lower())).first()
    if existing:
        vals = {"updated_at": now_utc()}
        if phone and not existing.phone:
            vals["phone"] = phone
        if sms_consent:
            vals["sms_consent"] = True
        conn.execute(sa.update(c).where(c.c.id == existing.id).values(**vals))
        return db.row(conn.execute(sa.select(c).where(c.c.id == existing.id)).first())
    cid = uuid.uuid4()
    conn.execute(sa.insert(c).values(id=cid, first_name=first_name.strip(), last_name=last_name.strip(),
                                     email=email or None, phone=(phone or "").strip() or None,
                                     sms_consent=bool(sms_consent), email_consent=False,
                                     status="lead", source=source, tags=[], notes=""))
    return db.row(conn.execute(sa.select(c).where(c.c.id == cid)).first())


# ---------- booking ----------
def book(conn, *, type_id, start_iso: str, first_name, last_name, email, phone="", mode="telehealth",
         message="", sms_consent=False, source="web", client_id=None, now=None) -> dict:
    t = get_type(conn, type_id=type_id)
    if not t or not t["active"]:
        raise SlotInvalid("That appointment type isn't available.")
    try:
        start = datetime.strptime(start_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise SlotInvalid("Invalid time.")
    local_day = start.astimezone(tz()).date()
    allowed = compute_slots(conn, t, local_day, local_day, now=now).get(local_day.isoformat(), [])
    if start_iso not in allowed:
        raise SlotTaken("That time is no longer available. Please pick another.")
    if t["mode"] in ("telehealth", "in_person"):
        mode = t["mode"]
    if mode not in ("telehealth", "in_person"):
        mode = "telehealth"
    end = start + timedelta(minutes=t["duration_min"])
    blocked = end + timedelta(minutes=t["buffer_after_min"])
    if client_id:
        client = db.row(conn.execute(sa.select(db.clients).where(db.clients.c.id == client_id)).first())
    else:
        client = upsert_client(conn, first_name, last_name, email, phone, sms_consent, source)
    aid = uuid.uuid4()
    try:
        with conn.begin_nested():
            conn.execute(sa.insert(db.appointments).values(
                id=aid, client_id=client["id"], type_id=t["id"], type_name=t["name"], start_at=start, end_at=end,
                blocked_until=blocked, status="confirmed", mode=mode, client_message=(message or "")[:1000],
                manage_token=secrets.token_urlsafe(24), source=source))
    except IntegrityError:
        raise SlotTaken("That time was just taken. Please pick another.")
    a = db.row(conn.execute(sa.select(db.appointments).where(db.appointments.c.id == aid)).first())
    a["client"] = client
    return a


def get_by_token(conn, token: str):
    r = conn.execute(sa.select(db.appointments).where(db.appointments.c.manage_token == token)).first()
    if not r:
        return None
    a = db.row(r)
    a["client"] = db.row(conn.execute(sa.select(db.clients).where(db.clients.c.id == a["client_id"])).first())
    return a


def cancel(conn, appt_id, reason_note: str = ""):
    conn.execute(sa.update(db.appointments).where(db.appointments.c.id == appt_id).values(
        status="cancelled", cancelled_at=now_utc()))


def reschedule(conn, appt: dict, new_start_iso: str) -> dict:
    """Move an appointment to a new slot. The old slot is released only if the new one is free."""
    t = get_type(conn, type_id=appt["type_id"])
    if not t:
        raise SlotInvalid("This appointment type no longer exists; please cancel and rebook.")
    start = datetime.strptime(new_start_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    local_day = start.astimezone(tz()).date()
    # temporarily treat own slot as free by computing against a cancelled copy
    a = db.appointments
    conn.execute(sa.update(a).where(a.c.id == appt["id"]).values(status="cancelled"))
    try:
        allowed = compute_slots(conn, t, local_day, local_day).get(local_day.isoformat(), [])
        if new_start_iso not in allowed:
            raise SlotTaken("That time is no longer available.")
        end = start + timedelta(minutes=t["duration_min"])
        blocked = end + timedelta(minutes=t["buffer_after_min"])
        with conn.begin_nested():
            conn.execute(sa.update(a).where(a.c.id == appt["id"]).values(
                start_at=start, end_at=end, blocked_until=blocked, status="confirmed",
                cancelled_at=None, reminder_sent_at=None))
    except (SlotTaken, IntegrityError) as e:
        conn.execute(sa.update(a).where(a.c.id == appt["id"]).values(status=appt["status"]))
        raise SlotTaken("That time is no longer available.") if isinstance(e, IntegrityError) else e
    return get_by_token(conn, appt["manage_token"])
