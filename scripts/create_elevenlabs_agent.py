"""Create Mia's ElevenLabs voice agent + tools.

Usage:
  export ELEVENLABS_API_KEY=...  AGENT_WEBHOOK_SECRET=...  SITE_URL=https://anavah-institute.org
  export ELEVENLABS_VOICE_ID=<warm voice id from your ElevenLabs Voice Library>   # strongly recommended
  python scripts/create_elevenlabs_agent.py            # creates tools + agent, prints agent_id
  python scripts/create_elevenlabs_agent.py --dry-run  # prints the payloads only
  python scripts/create_elevenlabs_agent.py --print-prompt   # prints the system prompt to paste into the dashboard

The request shapes follow ElevenLabs' current API reference (POST /v1/convai/tools, POST /v1/convai/agents/create).
If ElevenLabs changes a field, the API error is printed verbatim; every tool/prompt below can also be entered by hand
in the dashboard (Agents > your agent > Tools) using config/elevenlabs_agent.md.
"""
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.elevenlabs.io/v1"
SITE = os.environ.get("SITE_URL", "https://anavah-institute.org").rstrip("/")
SECRET = os.environ.get("AGENT_WEBHOOK_SECRET", "")
LLM = os.environ.get("ELEVENLABS_LLM", "gpt-4o")

VOICE_STYLE = """
VOICE & DELIVERY
- Speak slowly and warmly, like a calm, caring front-desk coordinator at a therapeutic practice.
- One idea per sentence. Pause after questions. Never rush or interrupt.
- Ask one question at a time. Confirm names, email (spell it back letter by letter) and phone before sending a callback request.

TOOLS
- request_callback(...): when the caller prefers the office to call them back. Collect first name, last name, phone and email only; nothing health-related.
- navigate_to(section): scroll the website to a section while the caller is on the site.
- open_booking(): open the page where they schedule an initial consultation on Phillip's Google Calendar. You cannot book appointments yourself.
Never ask for or record symptoms, diagnoses, medications, or insurance member IDs. Never quote prices (fees are discussed on the consultation call).
Early in every call, say once that you are not for emergencies: call 911, or call or text 988.
"""

FIRST_MESSAGE = "Hello, this is Mia, the virtual assistant for Anavah Institute. How can I help you today?"


def prompt_text() -> str:
    kb = (ROOT / "config" / "mia_knowledge.md").read_text(encoding="utf-8")
    kb = kb.split("## ACTION TOKENS")[0]  # action tokens are for text chat only
    return kb + VOICE_STYLE


def webhook(name, desc, path, props, required):
    return {"tool_config": {
        "type": "webhook", "name": name, "description": desc, "response_timeout_secs": 20,
        "api_schema": {
            "url": f"{SITE}{path}", "method": "POST", "content_type": "application/json",
            "request_headers": {"X-Agent-Secret": SECRET},
            "request_body_schema": {"type": "object", "property_kind": "object", "required": required,
                                    "properties": {k: {"type": "string", "description": v} for k, v in props.items()}}}}}


def client_tool(name, desc, props, required):
    return {"tool_config": {
        "type": "client", "name": name, "description": desc, "expects_response": True,
        "parameters": {"type": "object", "required": required,
                       "properties": {k: {"type": "string", "description": v} for k, v in props.items()}}}}


TOOLS = [
    webhook("request_callback", "Ask the office to call or email the person back.", "/api/agent/callback",
            {"first_name": "First name", "last_name": "Last name", "phone": "Phone number", "email": "Email address",
             "reason": "Short non-clinical reason, e.g. 'wants to schedule an intake'"}, ["first_name"]),
    client_tool("navigate_to", "Scroll the website to a section.",
                {"section": "One of: top, mission, services, about, appointments, insurance, contact"}, ["section"]),
    client_tool("open_booking", "Open the page where the caller schedules an initial consultation.", {}, []),
]


def main():
    if "--print-prompt" in sys.argv:
        print(prompt_text()); return
    dry = "--dry-run" in sys.argv
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not dry and not (key and SECRET):
        sys.exit("Set ELEVENLABS_API_KEY and AGENT_WEBHOOK_SECRET first (or use --dry-run).")
    headers = {"xi-api-key": key, "Content-Type": "application/json"}

    def post(path, body):
        if dry:
            print(f"POST {path}\n{json.dumps(body, indent=2)[:1500]}\n"); return {"id": "DRY", "agent_id": "DRY"}
        r = httpx.post(API + path, headers=headers, json=body, timeout=60)
        if r.status_code >= 400:
            sys.exit(f"ElevenLabs error {r.status_code} on {path}: {r.text[:800]}")
        return r.json()

    tool_ids = []
    for t in TOOLS:
        res = post("/convai/tools", t)
        tool_ids.append(res.get("id") or res.get("tool_id"))
        print("tool created:", t["tool_config"]["name"], tool_ids[-1])

    tts = {"model_id": os.environ.get("ELEVENLABS_TTS_MODEL", "eleven_v4_turbo")}
    if os.environ.get("ELEVENLABS_VOICE_ID"):
        tts["voice_id"] = os.environ["ELEVENLABS_VOICE_ID"]
    agent = post("/convai/agents/create", {
        "name": "Mia — Anavah Institute",
        "conversation_config": {
            "agent": {"first_message": FIRST_MESSAGE, "language": "en",
                      "prompt": {"prompt": prompt_text(), "llm": LLM, "tool_ids": tool_ids}},
            "tts": tts}})
    print("\nAgent created. ELEVENLABS_AGENT_ID =", agent.get("agent_id"))
    print("Next: in the ElevenLabs dashboard open the agent > Security: enable authentication and add your domain to the allowlist,"
          " then put the agent id in Render as ELEVENLABS_AGENT_ID.")


if __name__ == "__main__":
    main()
