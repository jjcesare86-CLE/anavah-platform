import csv
import io
import uuid
from datetime import date, datetime, timedelta, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from .. import auth, db, ghl, messaging, scheduling as sch
from ..config import settings
from ..util import rate_limit

router = APIRouter(prefix="/api/admin")
secured = APIRouter(dependencies=[Depends(auth.require_admin)])


def ser(v):
    if isinstance(v, dict):
        return {k: ser(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [ser(x) for x in v]
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return v


def eng():
    return db.get_engine()


def pick(body: dict, allowed: set) -> dict:
    return {k: v for k, v in body.items() if k in allowed}


def uid(s: str) -> uuid.UUID:
    try:
        return uuid.UUID(s)
    except ValueError:
        raise HTTPException(404, "Not found.")


# ---------- auth ----------
class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginIn, request: Request):
    rate_limit(request, "login", 10, 900)
    return auth.login(body.email, body.password)


@secured.get("/me")
def me(request: Request):
    return {"email": auth.require_admin(request), "dry_run": settings.dry_run, "ghl": ghl.configured(),
            "business_address_set": bool(settings.business_address), "timezone": settings.timezone}


# ---------- dashboard ----------
@secured.get("/dashboard")
def dashboard():
    z = sch.tz()
    now = sch.now_utc()
    day_start = datetime.now(z).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    A, C = db.appointments, db.clients
    with eng().connect() as conn:
        today = [db.row(r) for r in conn.execute(sa.select(A).where(
            A.c.start_at >= day_start, A.c.start_at < day_start + timedelta(days=1), A.c.status.in_(sch.LIVE)).order_by(A.c.start_at))]
        upcoming = [db.row(r) for r in conn.execute(sa.select(A).where(
            A.c.start_at >= now, A.c.status.in_(sch.LIVE)).order_by(A.c.start_at).limit(8))]
        names = {r.id: f"{r.first_name} {r.last_name}".strip() for r in conn.execute(sa.select(C.c.id, C.c.first_name, C.c.last_name))}
        for a in today + upcoming:
            a["client_name"] = names.get(a["client_id"], "")
        cnt = lambda q: conn.execute(q).scalar() or 0
        stats = {
            "today": len(today),
            "week": cnt(sa.select(sa.func.count()).select_from(A).where(A.c.start_at >= now, A.c.start_at < now + timedelta(days=7), A.c.status.in_(sch.LIVE))),
            "new_leads": cnt(sa.select(sa.func.count()).select_from(C).where(C.c.status == "lead")),
            "active_clients": cnt(sa.select(sa.func.count()).select_from(C).where(C.c.status == "active")),
            "prospects_open": cnt(sa.select(sa.func.count()).select_from(db.prospects).where(db.prospects.c.status.in_(("new", "contacted", "replied")))),
            "messages_today": cnt(sa.select(sa.func.count()).select_from(db.messages).where(db.messages.c.created_at >= day_start)),
        }
        recent = [db.row(r) for r in conn.execute(sa.select(db.clients).order_by(db.clients.c.created_at.desc()).limit(6))]
    return ser({"stats": stats, "today": today, "upcoming": upcoming, "recent_clients": recent})


# ---------- appointments ----------
@secured.get("/appointments")
def list_appts(start: date, end: date):
    z = sch.tz()
    s = datetime.combine(start, datetime.min.time(), tzinfo=z).astimezone(timezone.utc)
    e = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=z).astimezone(timezone.utc)
    A = db.appointments
    with eng().connect() as conn:
        rows = [db.row(r) for r in conn.execute(sa.select(A).where(A.c.start_at >= s, A.c.start_at < e).order_by(A.c.start_at))]
        names = {r.id: (f"{r.first_name} {r.last_name}".strip(), r.email, r.phone)
                 for r in conn.execute(sa.select(db.clients.c.id, db.clients.c.first_name, db.clients.c.last_name, db.clients.c.email, db.clients.c.phone))}
        off = [db.row(r) for r in conn.execute(sa.select(db.time_off).where(db.time_off.c.start_at < e, db.time_off.c.end_at > s))]
    for a in rows:
        n = names.get(a["client_id"], ("", "", ""))
        a["client_name"], a["client_email"], a["client_phone"] = n
        a.pop("manage_token", None)
    return ser({"appointments": rows, "time_off": off})


class AdminBook(BaseModel):
    client_id: str | None = None
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    type_id: str
    start: str
    mode: str = "telehealth"
    notes: str = ""
    notify: bool = True


@secured.post("/appointments")
def create_appt(body: AdminBook):
    with eng().begin() as conn:
        if not body.client_id and not (body.first_name and (body.email or body.phone)):
            raise HTTPException(422, "Choose a client, or enter a name plus email or phone.")
        try:
            a = sch.book(conn, type_id=uid(body.type_id), start_iso=body.start, first_name=body.first_name, last_name=body.last_name,
                         email=body.email, phone=body.phone, mode=body.mode, source="admin",
                         client_id=uid(body.client_id) if body.client_id else None)
        except (sch.SlotTaken, sch.SlotInvalid) as e:
            raise HTTPException(409, str(e))
        if body.notes:
            conn.execute(sa.update(db.appointments).where(db.appointments.c.id == a["id"]).values(notes=body.notes))
        if body.notify:
            messaging.notify_booking(conn, a)
    return ser({"id": a["id"]})


@secured.patch("/appointments/{aid}")
def patch_appt(aid: str, body: dict):
    A = db.appointments
    with eng().begin() as conn:
        r = conn.execute(sa.select(A).where(A.c.id == uid(aid))).first()
        if not r:
            raise HTTPException(404, "Not found.")
        a = db.row(r)
        vals = pick(body, {"notes", "status", "mode"})
        if vals.get("status") and vals["status"] not in ("pending", "confirmed", "cancelled", "completed", "no_show"):
            raise HTTPException(422, "Bad status.")
        if vals.get("status") == "cancelled":
            vals["cancelled_at"] = sch.now_utc()
        if vals.get("status") in sch.LIVE and a["status"] not in sch.LIVE:
            # re-activating: make sure the slot is still free
            clash = conn.execute(sa.select(A.c.id).where(A.c.id != a["id"], A.c.status.in_(sch.LIVE),
                                                         A.c.start_at < a["blocked_until"], A.c.blocked_until > a["start_at"])).first()
            if clash:
                raise HTTPException(409, "That time now overlaps another appointment.")
        if vals:
            conn.execute(sa.update(A).where(A.c.id == a["id"]).values(**vals))
        if body.get("start"):
            full = sch.get_by_token(conn, a["manage_token"])
            try:
                sch.reschedule(conn, full, body["start"])
            except sch.SlotTaken as e:
                raise HTTPException(409, str(e))
    return {"ok": True}


# ---------- generic person CRUD (clients & prospects) ----------
CLIENT_FIELDS = {"first_name", "last_name", "email", "phone", "status", "source", "tags", "notes",
                 "email_consent", "sms_consent", "do_not_contact"}
PROSPECT_FIELDS = {"name", "organization", "role", "category", "email", "phone", "status", "notes", "do_not_contact"}
CLIENT_STATUS = {"lead", "active", "inactive", "archived"}
PROSPECT_STATUS = {"new", "contacted", "replied", "meeting", "won", "lost"}


def _clean(vals: dict, status_set: set):
    for k in ("email", "phone"):
        if k in vals:
            vals[k] = (vals[k] or "").strip() or None
    if "status" in vals and vals["status"] not in status_set:
        raise HTTPException(422, "Bad status.")
    return vals


def _search(tbl, q: str, cols):
    like = f"%{q.lower()}%"
    return sa.or_(*[sa.func.lower(sa.func.coalesce(getattr(tbl.c, c), "")).like(like) for c in cols])


@secured.get("/clients")
def list_clients(q: str = "", status: str = "", limit: int = 200):
    T = db.clients
    s = sa.select(T).order_by(T.c.created_at.desc()).limit(min(limit, 500))
    if q:
        s = s.where(_search(T, q, ("first_name", "last_name", "email", "phone")))
    if status:
        s = s.where(T.c.status == status)
    with eng().connect() as conn:
        return ser({"clients": [db.row(r) for r in conn.execute(s)]})


@secured.post("/clients")
def create_client(body: dict):
    vals = _clean(pick(body, CLIENT_FIELDS), CLIENT_STATUS)
    if not (vals.get("first_name") or vals.get("last_name")):
        raise HTTPException(422, "A name is required.")
    vals.setdefault("tags", [])
    vals.setdefault("source", "manual")
    with eng().begin() as conn:
        if vals.get("email") and conn.execute(sa.select(db.clients.c.id).where(sa.func.lower(db.clients.c.email) == vals["email"].lower())).first():
            raise HTTPException(409, "A client with that email already exists.")
        cid = uuid.uuid4()
        conn.execute(sa.insert(db.clients).values(id=cid, **vals))
    return {"id": str(cid)}


@secured.get("/clients/{cid}")
def get_client(cid: str):
    with eng().connect() as conn:
        r = conn.execute(sa.select(db.clients).where(db.clients.c.id == uid(cid))).first()
        if not r:
            raise HTTPException(404, "Not found.")
        c = db.row(r)
        appts = [db.row(x) for x in conn.execute(sa.select(db.appointments).where(db.appointments.c.client_id == c["id"]).order_by(db.appointments.c.start_at.desc()))]
        for a in appts:
            a.pop("manage_token", None)
        notes = [db.row(x) for x in conn.execute(sa.select(db.client_notes).where(db.client_notes.c.client_id == c["id"]).order_by(db.client_notes.c.created_at.desc()))]
        msgs = [db.row(x) for x in conn.execute(sa.select(db.messages).where(db.messages.c.client_id == c["id"]).order_by(db.messages.c.created_at.desc()).limit(50))]
    return ser({"client": c, "appointments": appts, "notes": notes, "messages": msgs})


@secured.patch("/clients/{cid}")
def patch_client(cid: str, body: dict):
    vals = _clean(pick(body, CLIENT_FIELDS), CLIENT_STATUS)
    vals["updated_at"] = sch.now_utc()
    with eng().begin() as conn:
        res = conn.execute(sa.update(db.clients).where(db.clients.c.id == uid(cid)).values(**vals))
        if not res.rowcount:
            raise HTTPException(404, "Not found.")
    return {"ok": True}


@secured.delete("/clients/{cid}")
def archive_client(cid: str):
    with eng().begin() as conn:
        conn.execute(sa.update(db.clients).where(db.clients.c.id == uid(cid)).values(status="archived", updated_at=sch.now_utc()))
    return {"ok": True}


class NoteIn(BaseModel):
    body: str


@secured.post("/clients/{cid}/notes")
def add_note(cid: str, n: NoteIn, request: Request):
    if not n.body.strip():
        raise HTTPException(422, "Note is empty.")
    with eng().begin() as conn:
        conn.execute(sa.insert(db.client_notes).values(client_id=uid(cid), body=n.body.strip()[:4000], created_by=auth.require_admin(request)))
    return {"ok": True}


@secured.get("/export/clients.csv")
def export_clients():
    with eng().connect() as conn:
        rows = [db.row(r) for r in conn.execute(sa.select(db.clients).order_by(db.clients.c.created_at))]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["first_name", "last_name", "email", "phone", "status", "source", "email_consent", "sms_consent", "do_not_contact", "created_at"])
    for r in rows:
        w.writerow([r["first_name"], r["last_name"], r["email"] or "", r["phone"] or "", r["status"], r["source"],
                    r["email_consent"], r["sms_consent"], r["do_not_contact"], ser(r["created_at"])])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="clients.csv"'})


# ---------- prospects ----------
@secured.get("/prospects")
def list_prospects(q: str = "", status: str = "", category: str = ""):
    T = db.prospects
    s = sa.select(T).order_by(T.c.created_at.desc()).limit(500)
    if q:
        s = s.where(_search(T, q, ("name", "organization", "email", "role")))
    if status:
        s = s.where(T.c.status == status)
    if category:
        s = s.where(T.c.category == category)
    with eng().connect() as conn:
        return ser({"prospects": [db.row(r) for r in conn.execute(s)]})


@secured.post("/prospects")
def create_prospect(body: dict):
    vals = _clean(pick(body, PROSPECT_FIELDS), PROSPECT_STATUS)
    if not (vals.get("name") or "").strip():
        raise HTTPException(422, "A name is required.")
    with eng().begin() as conn:
        pid = uuid.uuid4()
        conn.execute(sa.insert(db.prospects).values(id=pid, **vals))
    return {"id": str(pid)}


@secured.patch("/prospects/{pid}")
def patch_prospect(pid: str, body: dict):
    vals = _clean(pick(body, PROSPECT_FIELDS), PROSPECT_STATUS)
    vals["updated_at"] = sch.now_utc()
    with eng().begin() as conn:
        if not conn.execute(sa.update(db.prospects).where(db.prospects.c.id == uid(pid)).values(**vals)).rowcount:
            raise HTTPException(404, "Not found.")
    return {"ok": True}


@secured.delete("/prospects/{pid}")
def delete_prospect(pid: str):
    with eng().begin() as conn:
        conn.execute(sa.delete(db.prospects).where(db.prospects.c.id == uid(pid)))
    return {"ok": True}


class ImportIn(BaseModel):
    csv: str
    category: str = "provider"


@secured.post("/prospects/import")
def import_prospects(body: ImportIn):
    """CSV with a header row. Recognised columns: name, organization, role, email, phone, category, notes."""
    reader = csv.DictReader(io.StringIO(body.csv.strip()))
    added = skipped = 0
    with eng().begin() as conn:
        seen = {(r[0] or "").lower() for r in conn.execute(sa.select(db.prospects.c.email))}
        for rec in reader:
            rec = {(k or "").strip().lower(): (v or "").strip() for k, v in rec.items()}
            name = rec.get("name") or (rec.get("first_name", "") + " " + rec.get("last_name", "")).strip()
            email = rec.get("email", "")
            if not name or (email and email.lower() in seen):
                skipped += 1
                continue
            cat = rec.get("category") or body.category
            conn.execute(sa.insert(db.prospects).values(
                name=name, organization=rec.get("organization", ""), role=rec.get("role", ""),
                category=cat if cat in ("provider", "attorney", "pt", "pcp", "organization", "other") else "other",
                email=email or None, phone=rec.get("phone") or None, notes=rec.get("notes", "")))
            if email:
                seen.add(email.lower())
            added += 1
    return {"added": added, "skipped": skipped}


# ---------- templates ----------
@secured.get("/templates")
def list_templates():
    with eng().connect() as conn:
        return ser({"templates": [db.row(r) for r in conn.execute(sa.select(db.templates).order_by(db.templates.c.created_at))]})


@secured.post("/templates")
def create_template(body: dict):
    vals = pick(body, {"name", "channel", "subject", "body"})
    if vals.get("channel") not in ("email", "sms") or not vals.get("name") or not vals.get("body"):
        raise HTTPException(422, "Name, channel (email/sms) and body are required.")
    with eng().begin() as conn:
        tid = uuid.uuid4()
        conn.execute(sa.insert(db.templates).values(id=tid, **vals))
    return {"id": str(tid)}


@secured.patch("/templates/{tid}")
def patch_template(tid: str, body: dict):
    vals = pick(body, {"name", "subject", "body"})
    with eng().begin() as conn:
        conn.execute(sa.update(db.templates).where(db.templates.c.id == uid(tid)).values(**vals))
    return {"ok": True}


@secured.delete("/templates/{tid}")
def delete_template(tid: str):
    with eng().begin() as conn:
        conn.execute(sa.delete(db.templates).where(db.templates.c.id == uid(tid)))
    return {"ok": True}


# ---------- outreach ----------
class Recipient(BaseModel):
    type: str  # client | prospect
    id: str


class OutreachIn(BaseModel):
    channel: str
    subject: str = ""
    body: str
    recipients: list[Recipient]
    preview: bool = False


@secured.post("/outreach/send")
def outreach(body: OutreachIn):
    if body.channel not in ("email", "sms"):
        raise HTTPException(422, "Channel must be email or sms.")
    if not body.body.strip():
        raise HTTPException(422, "Message body is empty.")
    if len(body.recipients) > 200:
        raise HTTPException(422, "Send to at most 200 recipients at a time.")
    results = []
    with eng().begin() as conn:
        for rc in body.recipients:
            tbl = db.clients if rc.type == "client" else db.prospects
            r = conn.execute(sa.select(tbl).where(tbl.c.id == uid(rc.id))).first()
            if not r:
                results.append({"id": rc.id, "status": "blocked", "error": "Not found."})
                continue
            person = db.row(r)
            ctx = messaging.base_ctx(person)
            subj, text = messaging.render(body.subject, ctx), messaging.render(body.body, ctx)
            to = person.get("email") if body.channel == "email" else person.get("phone")
            name = person.get("name") or f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
            if body.preview:
                results.append({"id": rc.id, "name": name, "to": to, "subject": subj, "body": text})
                continue
            res = messaging.send(conn, channel=body.channel, to=to or "", subject=subj, body=text, kind="outreach",
                                 client=person if rc.type == "client" else None, prospect=person if rc.type == "prospect" else None)
            if res["status"] in ("sent", "dry_run") and rc.type == "prospect" and person["status"] == "new":
                conn.execute(sa.update(db.prospects).where(db.prospects.c.id == person["id"]).values(status="contacted"))
            results.append({**res, "message_id": res["id"], "id": rc.id, "name": name})
    summary = {}
    for x in results:
        summary[x.get("status", "preview")] = summary.get(x.get("status", "preview"), 0) + 1
    return ser({"results": results, "summary": summary, "dry_run": settings.dry_run})


@secured.get("/messages")
def list_messages(limit: int = 100, kind: str = ""):
    s = sa.select(db.messages).order_by(db.messages.c.created_at.desc()).limit(min(limit, 300))
    if kind:
        s = s.where(db.messages.c.kind == kind)
    with eng().connect() as conn:
        return ser({"messages": [db.row(r) for r in conn.execute(s)]})


# ---------- availability & settings ----------
@secured.get("/schedule")
def get_schedule():
    with eng().connect() as conn:
        rules = [db.row(r) for r in conn.execute(sa.select(db.availability_rules).order_by(db.availability_rules.c.weekday, db.availability_rules.c.start_time))]
        off = [db.row(r) for r in conn.execute(sa.select(db.time_off).where(db.time_off.c.end_at >= sch.now_utc()).order_by(db.time_off.c.start_at))]
        types = sch.list_types(conn, active_only=False)
        cfg = sch.booking_settings(conn)
    return ser({"rules": rules, "time_off": off, "types": types, "booking": cfg})


class RulesIn(BaseModel):
    rules: list[dict]


@secured.put("/schedule/rules")
def put_rules(body: RulesIn):
    clean = []
    for r in body.rules:
        try:
            wd = int(r["weekday"])
            s, e = str(r["start_time"]), str(r["end_time"])
            sch._hm(s), sch._hm(e)
        except (KeyError, ValueError):
            raise HTTPException(422, "Each rule needs weekday (0-6) and HH:MM start/end.")
        if not 0 <= wd <= 6 or sch._hm(e) <= sch._hm(s):
            raise HTTPException(422, "Invalid weekday or end time before start time.")
        clean.append({"weekday": wd, "start_time": s, "end_time": e, "active": bool(r.get("active", True))})
    with eng().begin() as conn:
        conn.execute(sa.delete(db.availability_rules))
        for r in clean:
            conn.execute(sa.insert(db.availability_rules).values(**r))
    return {"ok": True}


class OffIn(BaseModel):
    start: str
    end: str
    reason: str = ""


@secured.post("/schedule/time-off")
def add_time_off(body: OffIn):
    try:
        s = datetime.fromisoformat(body.start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(body.end.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(422, "Bad date.")
    if s.tzinfo is None:
        s = s.replace(tzinfo=sch.tz())
    if e.tzinfo is None:
        e = e.replace(tzinfo=sch.tz())
    if e <= s:
        raise HTTPException(422, "End must be after start.")
    with eng().begin() as conn:
        oid = uuid.uuid4()
        conn.execute(sa.insert(db.time_off).values(id=oid, start_at=s.astimezone(timezone.utc), end_at=e.astimezone(timezone.utc), reason=body.reason))
    return {"id": str(oid)}


@secured.delete("/schedule/time-off/{oid}")
def del_time_off(oid: str):
    with eng().begin() as conn:
        conn.execute(sa.delete(db.time_off).where(db.time_off.c.id == uid(oid)))
    return {"ok": True}


@secured.put("/schedule/booking")
def put_booking(body: dict):
    cfg = {}
    for k, lo, hi in (("min_notice_hours", 0, 720), ("max_advance_days", 1, 365), ("slot_step_min", 5, 120)):
        if k in body:
            try:
                cfg[k] = max(lo, min(hi, int(body[k])))
            except (TypeError, ValueError):
                raise HTTPException(422, f"{k} must be a number.")
    with eng().begin() as conn:
        sch.put_setting(conn, "booking", {**sch.booking_settings(conn), **cfg})
    return {"ok": True}


TYPE_FIELDS = {"name", "slug", "description", "audience", "duration_min", "buffer_after_min", "mode", "active", "sort"}


@secured.post("/types")
def create_type(body: dict):
    vals = pick(body, TYPE_FIELDS)
    if not vals.get("name"):
        raise HTTPException(422, "Name is required.")
    vals.setdefault("slug", "".join(ch if ch.isalnum() else "-" for ch in vals["name"].lower()).strip("-"))
    with eng().begin() as conn:
        if conn.execute(sa.select(db.appointment_types.c.id).where(db.appointment_types.c.slug == vals["slug"])).first():
            raise HTTPException(409, "A type with that slug exists.")
        tid = uuid.uuid4()
        conn.execute(sa.insert(db.appointment_types).values(id=tid, **vals))
    return {"id": str(tid)}


@secured.patch("/types/{tid}")
def patch_type(tid: str, body: dict):
    vals = pick(body, TYPE_FIELDS - {"slug"})
    for k in ("duration_min", "buffer_after_min", "sort"):
        if k in vals:
            vals[k] = int(vals[k])
    if "duration_min" in vals and not 5 <= vals["duration_min"] <= 480:
        raise HTTPException(422, "Duration must be 5-480 minutes.")
    with eng().begin() as conn:
        conn.execute(sa.update(db.appointment_types).where(db.appointment_types.c.id == uid(tid)).values(**vals))
    return {"ok": True}


# ---------- GHL ----------
@secured.post("/ghl/test")
def ghl_test():
    try:
        return ghl.test_connection()
    except ghl.GHLError as e:
        raise HTTPException(502, str(e))


@secured.post("/ghl/sync")
def ghl_sync():
    """Push every non-archived client without a GHL contact id into GHL (creates/updates contacts, tags 'anavah-client')."""
    synced, failed = 0, []
    with eng().begin() as conn:
        rows = [db.row(r) for r in conn.execute(sa.select(db.clients).where(db.clients.c.status != "archived", db.clients.c.ghl_contact_id.is_(None)).limit(300))]
        for c in rows:
            if not (c.get("email") or c.get("phone")):
                continue
            try:
                cid = ghl.upsert_contact(c["first_name"], c["last_name"], c.get("email"), c.get("phone"), tags=["anavah-client"])
                conn.execute(sa.update(db.clients).where(db.clients.c.id == c["id"]).values(ghl_contact_id=cid))
                synced += 1
            except ghl.GHLError as e:
                failed.append(str(e)[:120])
                if len(failed) >= 3:
                    break
    return {"synced": synced, "failed": failed}


router.include_router(secured)
