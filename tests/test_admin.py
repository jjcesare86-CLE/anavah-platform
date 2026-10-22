from datetime import datetime, timedelta, timezone

from app import jobs, db
import sqlalchemy as sa


def mk_client(client, admin, **kw):
    body = {"first_name": "Cy", "last_name": "Client", "email": "cy@example.com", "phone": "2125550123", **kw}
    r = client.post("/api/admin/clients", json=body, headers=admin)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_admin_requires_auth(client):
    assert client.get("/api/admin/clients").status_code == 401
    assert client.get("/api/admin/clients", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/admin/dashboard", headers={"Authorization": "Bearer devtok"}).status_code == 200


def test_client_crud_notes_archive(client, admin):
    cid = mk_client(client, admin)
    assert client.post("/api/admin/clients", json={"first_name": "Dup", "email": "CY@example.com"}, headers=admin).status_code == 409
    client.patch(f"/api/admin/clients/{cid}", json={"status": "active", "tags": ["vip"], "bogus": "x"}, headers=admin)
    client.post(f"/api/admin/clients/{cid}/notes", json={"body": "Prefers mornings"}, headers=admin)
    d = client.get(f"/api/admin/clients/{cid}", headers=admin).json()
    assert d["client"]["status"] == "active" and d["client"]["tags"] == ["vip"]
    assert d["notes"][0]["body"] == "Prefers mornings"
    assert client.patch(f"/api/admin/clients/{cid}", json={"status": "weird"}, headers=admin).status_code == 422
    client.delete(f"/api/admin/clients/{cid}", headers=admin)
    assert client.get("/api/admin/clients", params={"status": "archived"}, headers=admin).json()["clients"][0]["id"] == cid
    assert "cy@example.com" in client.get("/api/admin/export/clients.csv", headers=admin).text


def test_admin_books_for_client_and_calendar_lists_it(client, admin):
    cid = mk_client(client, admin)
    types = client.get("/api/admin/schedule", headers=admin).json()["types"]
    t = next(x for x in types if x["slug"] == "psychiatric-follow-up")
    slots = client.get("/api/public/slots", params={"type": t["slug"]}).json()["days"]
    day = sorted(slots)[0]
    r = client.post("/api/admin/appointments", json={"client_id": cid, "type_id": t["id"], "start": slots[day][0], "notes": "x"}, headers=admin)
    assert r.status_code == 200, r.text
    cal = client.get("/api/admin/appointments", params={"start": day, "end": day}, headers=admin).json()
    assert cal["appointments"][0]["client_name"] == "Cy Client" and "manage_token" not in cal["appointments"][0]
    aid = r.json()["id"]
    assert client.patch(f"/api/admin/appointments/{aid}", json={"status": "completed"}, headers=admin).status_code == 200


def test_schedule_rules_time_off_blocks_slots(client, admin):
    day = sorted(client.get("/api/public/slots", params={"type": "psychiatric-follow-up"}).json()["days"])[0]
    r = client.post("/api/admin/schedule/time-off", json={"start": f"{day}T00:00:00", "end": f"{day}T23:59:00", "reason": "Out"}, headers=admin)
    assert r.status_code == 200
    assert day not in client.get("/api/public/slots", params={"type": "psychiatric-follow-up"}).json()["days"]
    bad = client.put("/api/admin/schedule/rules", json={"rules": [{"weekday": 1, "start_time": "10:00", "end_time": "09:00"}]}, headers=admin)
    assert bad.status_code == 422
    ok = client.put("/api/admin/schedule/rules", json={"rules": [{"weekday": 6, "start_time": "10:00", "end_time": "12:00"}]}, headers=admin)
    assert ok.status_code == 200
    days = client.get("/api/public/slots", params={"type": "psychiatric-follow-up", "days": 21}).json()["days"]
    assert days and all(datetime.fromisoformat(d).weekday() == 6 for d in days)


def send(client, admin, recipients, channel="email"):
    return client.post("/api/admin/outreach/send", headers=admin, json={
        "channel": channel, "subject": "Hi {{first_name}}", "body": "Hello {{first_name}}, book: {{booking_link}}", "recipients": recipients}).json()


def test_outreach_consent_rules(client, admin):
    no_consent = mk_client(client, admin, email="a@example.com")
    consent = mk_client(client, admin, email="b@example.com", email_consent=True)
    dnc = mk_client(client, admin, email="c@example.com", email_consent=True, do_not_contact=True)
    sms_ok = mk_client(client, admin, email="d@example.com", sms_consent=True)
    res = send(client, admin, [{"type": "client", "id": i} for i in (no_consent, consent, dnc)])
    st = {r["id"]: r["status"] for r in res["results"]}
    assert st[no_consent] == "blocked" and st[dnc] == "blocked" and st[consent] == "dry_run"
    assert res["dry_run"] is True
    s = send(client, admin, [{"type": "client", "id": i} for i in (no_consent, sms_ok)], channel="sms")
    st = {r["id"]: r["status"] for r in s["results"]}
    assert st[no_consent] == "blocked" and st[sms_ok] == "dry_run"
    msgs = client.get("/api/admin/messages", headers=admin).json()["messages"]
    em = next(m for m in msgs if m["to_address"] == "b@example.com")
    assert "Unsubscribe:" in em["body"] and "123 W 23rd St" in em["body"] and "Hello Cy" in em["body"]


def test_prospect_import_outreach_unsubscribe_and_cap(client, admin, monkeypatch):
    csv_text = "name,organization,email,category\nDr. Lee,Lee PT,lee@pt.example,pt\nDr. Kim,Kim Law,kim@law.example,attorney\n,,,\n"
    r = client.post("/api/admin/prospects/import", json={"csv": csv_text}, headers=admin).json()
    assert r == {"added": 2, "skipped": 1}
    assert client.post("/api/admin/prospects/import", json={"csv": csv_text}, headers=admin).json()["added"] == 0
    ps = client.get("/api/admin/prospects", headers=admin).json()["prospects"]
    res = send(client, admin, [{"type": "prospect", "id": p["id"]} for p in ps])
    assert res["summary"] == {"dry_run": 2}
    assert all(p["status"] == "contacted" for p in client.get("/api/admin/prospects", headers=admin).json()["prospects"])
    # unsubscribe link works and then blocks
    from app import messaging
    tok = messaging.unsub_token("lee@pt.example")
    assert client.get("/unsubscribe", params={"t": tok}).status_code == 200
    assert client.post("/unsubscribe", params={"t": tok}).status_code == 200
    again = send(client, admin, [{"type": "prospect", "id": p["id"]} for p in ps])
    assert again["summary"] == {"dry_run": 1, "blocked": 1}
    assert client.post("/unsubscribe", params={"t": "garbage"}).status_code == 400
    # sms to prospects is never allowed
    assert send(client, admin, [{"type": "prospect", "id": ps[0]["id"]}], channel="sms")["summary"] == {"blocked": 1}
    # daily cap
    monkeypatch.setenv("OUTREACH_DAILY_CAP", "1")
    assert "blocked" in send(client, admin, [{"type": "prospect", "id": ps[1]["id"]}])["summary"]


def test_outreach_blocked_without_business_address(client, admin, monkeypatch):
    monkeypatch.setenv("BUSINESS_ADDRESS", "")
    cid = mk_client(client, admin, email_consent=True)
    res = send(client, admin, [{"type": "client", "id": cid}])
    assert res["results"][0]["status"] == "blocked" and "CAN-SPAM" in res["results"][0]["error"]


def test_reminders_job_once(client, admin):
    cid = mk_client(client, admin, sms_consent=True)
    types = client.get("/api/admin/schedule", headers=admin).json()["types"]
    t = types[0]
    A = db.appointments
    start = datetime.now(timezone.utc) + timedelta(hours=5)
    with db.get_engine().begin() as conn:
        conn.execute(sa.insert(A).values(client_id=__import__("uuid").UUID(cid), type_id=__import__("uuid").UUID(t["id"]), type_name=t["name"],
                                         start_at=start, end_at=start + timedelta(minutes=30), blocked_until=start + timedelta(minutes=30),
                                         status="confirmed", mode="telehealth", manage_token="tok123", source="admin"))
    assert jobs.run_reminders()["reminders_sent"] == 1
    assert jobs.run_reminders()["reminders_sent"] == 0
    kinds = [(m["channel"], m["kind"], m["status"]) for m in client.get("/api/admin/messages", headers=admin).json()["messages"]]
    assert ("email", "reminder", "dry_run") in kinds and ("sms", "reminder", "dry_run") in kinds


def test_pages_and_security(client):
    for p in ("/", "/book", "/manage", "/privacy", "/terms", "/admin", "/healthz", "/robots.txt"):
        assert client.get(p).status_code == 200, p
    assert client.get("/nope").status_code == 404
    assert client.get("/api/nope").json()["detail"]
    assert client.get("/admin").headers["x-robots-tag"].startswith("noindex")
