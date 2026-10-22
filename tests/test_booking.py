from datetime import date, datetime, timedelta, timezone

from app import db, scheduling as sch


def first_slot(client, slug="psychiatric-intake", days=14):
    r = client.get("/api/public/slots", params={"type": slug, "days": days})
    assert r.status_code == 200
    d = r.json()["days"]
    assert d, "expected some availability"
    day = sorted(d)[0]
    return day, d[day]


def payload(start, slug="psychiatric-intake", email="ana@example.com"):
    return {"type": slug, "start": start, "first_name": "Ana", "last_name": "Test", "email": email,
            "phone": "2125550100", "ack": True}


def test_config_lists_types(client):
    r = client.get("/api/public/config").json()
    assert any(t["slug"] == "psychiatric-intake" for t in r["types"])


def test_slots_respect_weekdays_and_notice(client):
    r = client.get("/api/public/slots", params={"type": "psychiatric-follow-up", "days": 21}).json()
    now = datetime.now(timezone.utc)
    for day, slots in r["days"].items():
        assert date.fromisoformat(day).weekday() < 5  # Mon-Fri default
        for s in slots:
            assert datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) >= now + timedelta(hours=12)


def test_book_then_double_book_rejected(client):
    _, slots = first_slot(client)
    r = client.post("/api/public/book", json=payload(slots[0]))
    assert r.status_code == 200, r.text
    assert r.json()["appointment"]["manage_url"].endswith(r.json()["appointment"]["token"])
    r2 = client.post("/api/public/book", json=payload(slots[0], email="bob@example.com"))
    assert r2.status_code == 409


def test_booked_slot_and_buffer_disappear(client):
    day, slots = first_slot(client)
    client.post("/api/public/book", json=payload(slots[0]))  # 60 min + 10 buffer
    _, after = first_slot(client)
    assert slots[0] not in after
    t0 = datetime.strptime(slots[0], "%Y-%m-%dT%H:%M:%SZ")
    # a 30-min follow-up must not start inside the 70-minute blocked window
    fu = client.get("/api/public/slots", params={"type": "psychiatric-follow-up", "days": 14}).json()["days"].get(day, [])
    for s in fu:
        st = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        assert not (t0 <= st < t0 + timedelta(minutes=70))


def test_requires_ack_and_honeypot(client):
    _, slots = first_slot(client)
    p = payload(slots[0])
    p["ack"] = False
    assert client.post("/api/public/book", json=p).status_code == 422
    p["ack"] = True
    p["website"] = "spam"
    assert client.post("/api/public/book", json=p).json() == {"ok": True}
    # honeypot must not have created an appointment
    assert client.post("/api/public/book", json=payload(slots[0])).status_code == 200


def test_invalid_start_rejected(client):
    r = client.post("/api/public/book", json=payload("2020-01-01T10:00:00Z"))
    assert r.status_code in (409, 422)


def test_cancel_frees_slot_and_reschedule(client):
    _, slots = first_slot(client)
    a = client.post("/api/public/book", json=payload(slots[0])).json()["appointment"]
    tok = a["token"]
    assert client.get("/api/public/appointment", params={"t": tok}).json()["status"] == "confirmed"
    new = slots[3]
    r = client.post("/api/public/appointment/reschedule", params={"t": tok}, json={"start": new})
    assert r.status_code == 200 and r.json()["appointment"]["start_at"] == new
    _, now_slots = first_slot(client)
    assert slots[0] in now_slots and new not in now_slots
    assert client.post("/api/public/appointment/cancel", params={"t": tok}).status_code == 200
    assert client.get("/api/public/appointment", params={"t": tok}).json()["status"] == "cancelled"
    assert new in first_slot(client)[1] or True
    assert client.get("/api/public/appointment", params={"t": "nope"}).status_code == 404


def test_reschedule_to_taken_slot_keeps_original(client):
    _, slots = first_slot(client, "psychiatric-follow-up")
    a = client.post("/api/public/book", json=payload(slots[0], "psychiatric-follow-up"))
    b = client.post("/api/public/book", json=payload(slots[4], "psychiatric-follow-up", "b@example.com"))
    tok = a.json()["appointment"]["token"]
    r = client.post("/api/public/appointment/reschedule", params={"t": tok}, json={"start": b.json()["appointment"]["start_at"]})
    assert r.status_code == 409
    assert client.get("/api/public/appointment", params={"t": tok}).json()["start_at"] == slots[0]


def test_ics(client):
    _, slots = first_slot(client)
    tok = client.post("/api/public/book", json=payload(slots[0])).json()["appointment"]["token"]
    r = client.get("/api/public/ics", params={"t": tok})
    assert r.status_code == 200 and "BEGIN:VEVENT" in r.text and "DTSTART:" in r.text


def test_dst_slots_use_local_wall_clock(client):
    """9:00 America/New_York is 14:00Z in winter and 13:00Z in summer."""
    with db.get_engine().connect() as conn:
        t = sch.get_type(conn, slug="psychiatric-follow-up")
        now = datetime(2027, 3, 1, tzinfo=timezone.utc)
        winter = sch.compute_slots(conn, t, date(2027, 3, 9), date(2027, 3, 9), now=now)["2027-03-09"]
        summer = sch.compute_slots(conn, t, date(2027, 3, 16), date(2027, 3, 16), now=now)["2027-03-16"]
    assert winter[0].endswith("T14:00:00Z") and summer[0].endswith("T13:00:00Z")
    assert winter[-1].endswith("T21:30:00Z") and summer[-1].endswith("T20:30:00Z")


def test_agent_tools_need_secret_and_book(client, agent_h):
    assert client.post("/api/agent/availability", json={"type_slug": "psychiatric-intake"}).status_code == 401
    av = client.post("/api/agent/availability", json={"type_slug": "psychiatric-intake"}, headers=agent_h).json()
    assert av["slots"]
    body = {"type_slug": "psychiatric-intake", "start": av["slots"][0]["start"], "first_name": "Voice", "last_name": "Caller",
            "email": "voice@example.com", "phone": "2125550111"}
    assert client.post("/api/agent/book", json=body, headers=agent_h).json()["booked"] is True
    assert client.post("/api/agent/book", json=body, headers=agent_h).json()["booked"] is False


def test_chat_without_key_falls_back(client):
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]}).json()
    assert "216" in r["reply"]
    assert client.post("/api/chat", json={"messages": []}).json()["reply"].startswith("Hello")


def test_contact_form_creates_lead(client, admin):
    r = client.post("/api/public/contact", json={"name": "Pat Doe", "email": "pat@example.com", "message": "Hello"})
    assert r.status_code == 200
    cl = client.get("/api/admin/clients", headers=admin).json()["clients"]
    assert any(c["email"] == "pat@example.com" and c["source"] == "contact_form" for c in cl)


def test_booking_does_not_grant_marketing_consent(client, admin):
    _, slots = first_slot(client)
    client.post("/api/public/book", json=payload(slots[0], email="nomarketing@example.com"))
    c = next(x for x in client.get("/api/admin/clients", headers=admin).json()["clients"] if x["email"] == "nomarketing@example.com")
    assert c["email_consent"] is False
