"""Default deployment: scheduling is handled by the Google Calendar booking page (BOOKING_MODE=google)."""
import json
from pathlib import Path

import pytest

PRACTICE = json.loads((Path(__file__).resolve().parent.parent / "config" / "practice.json").read_text())


@pytest.fixture()
def gclient(client, monkeypatch):
    monkeypatch.setenv("BOOKING_MODE", "google")
    return client


def test_internal_booking_endpoints_are_gone(gclient):
    assert gclient.get("/api/public/slots", params={"type": "psychiatric-intake"}).status_code == 410
    assert gclient.post("/api/public/book", json={}).status_code == 410
    assert gclient.get("/api/public/appointment", params={"t": "x"}).status_code == 410


def test_public_config_points_to_google(gclient):
    c = gclient.get("/api/public/config").json()
    assert c["booking_mode"] == "google" and c["booking_url"] == PRACTICE["booking_url"]


def test_voice_agent_never_books_directly(gclient, agent_h):
    av = gclient.post("/api/agent/availability", json={"type_slug": "psychiatric-intake"}, headers=agent_h).json()
    assert av["slots"] == [] and av["booking_url"] == PRACTICE["booking_url"]
    b = gclient.post("/api/agent/book", headers=agent_h, json={"type_slug": "x", "start": "x", "first_name": "A", "last_name": "B", "email": "a@b.co"}).json()
    assert b["booked"] is False


def test_contact_form_still_works(gclient, admin):
    assert gclient.post("/api/public/contact", json={"name": "Pat Doe", "email": "pat@example.com", "message": "Hello"}).status_code == 200


def test_practice_facts():
    assert PRACTICE["phone"] == "(216) 625-0028" and PRACTICE["fax"] == "(216) 625-0053"
    assert PRACTICE["email"] == "Scherb@anavah-institute.org"
