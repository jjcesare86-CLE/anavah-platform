"""Cron entrypoint (Render cron job): `python -m app.jobs`

Sends a reminder for every confirmed appointment starting in the next ~24h that hasn't had one.
Email always (transactional). SMS only if the client has recorded sms_consent.
"""
from datetime import timedelta

import sqlalchemy as sa

from . import db, messaging, scheduling as sch
from .config import PRACTICE, settings

WINDOW_HOURS = 24


def run_reminders(now=None) -> dict:
    now = now or sch.now_utc()
    A = db.appointments
    sent = skipped = 0
    with db.get_engine().begin() as conn:
        due = [db.row(r) for r in conn.execute(sa.select(A).where(
            A.c.status == "confirmed", A.c.reminder_sent_at.is_(None),
            A.c.start_at > now, A.c.start_at <= now + timedelta(hours=WINDOW_HOURS)))]
        for a in due:
            c = db.row(conn.execute(sa.select(db.clients).where(db.clients.c.id == a["client_id"])).first())
            a["client"] = c
            ctx = messaging.base_ctx(c, a)
            did = False
            if c.get("email"):
                r = messaging.send(conn, channel="email", to=c["email"], subject=f"Reminder: your appointment {ctx['when']}",
                                   body=(f"Hello {ctx['first_name']},\n\nThis is a reminder of your {a['type_name']} on {ctx['when']} "
                                         f"({'telehealth' if a['mode'] == 'telehealth' else 'in person, ' + PRACTICE['location']}).\n\n"
                                         f"Change or cancel: {ctx['manage_link']}\n\n{PRACTICE['name']} · {PRACTICE['phone']}"),
                                   kind="reminder", client=c, appt=a)
                did = did or r["status"] in ("sent", "dry_run")
            if c.get("phone") and c.get("sms_consent"):
                r = messaging.send(conn, channel="sms", to=c["phone"], subject="",
                                   body=f"Anavah Institute: reminder of your {a['type_name']} on {ctx['when']}. Manage: {ctx['manage_link']} Reply STOP to opt out.",
                                   kind="reminder", client=c, appt=a)
                did = did or r["status"] in ("sent", "dry_run")
            if did:
                conn.execute(sa.update(A).where(A.c.id == a["id"]).values(reminder_sent_at=now))
                sent += 1
            else:
                skipped += 1
    return {"reminders_sent": sent, "skipped": skipped, "dry_run": settings.dry_run}


if __name__ == "__main__":
    print(run_reminders())
