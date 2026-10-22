"""Mia text chat: Anthropic Messages API with the knowledge base as the system prompt."""
import re

import httpx

from .config import ROOT, settings

KB_PATH = ROOT / "config" / "mia_knowledge.md"
ACTION_RE = re.compile(r"\[\[(nav:#[a-z]+|book(?::[a-z\-]+)?|call)\]\]")
FALLBACK = ("I'm having trouble right now. You can reach the office at (216) 625-0028 or "
            "Scherb@anavah-institute.org, and I'm happy to help you find a time on the booking page.")


def knowledge() -> str:
    return KB_PATH.read_text(encoding="utf-8")


def system_prompt() -> str:
    return (knowledge() + "\n\nRespond in 1-3 short sentences unless asked for more. Plain text only, no markdown. "
            "You are in a website chat widget.")


def clean_history(msgs: list[dict]) -> list[dict]:
    out = []
    for m in msgs[-14:]:
        role = "assistant" if m.get("role") == "assistant" else "user"
        content = str(m.get("content", ""))[:1500].strip()
        if not content:
            continue
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n" + content
        else:
            out.append({"role": role, "content": content})
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def split_actions(text: str) -> tuple[str, list[str]]:
    actions = [m.group(1) for m in ACTION_RE.finditer(text)]
    return ACTION_RE.sub("", text).strip(), actions


def chat(messages: list[dict]) -> dict:
    hist = clean_history(messages)
    if not hist:
        return {"reply": "Hello, I'm Mia. How can I help you today?", "actions": []}
    if not settings.anthropic_key:
        return {"reply": FALLBACK, "actions": ["call"]}
    try:
        r = httpx.post("https://api.anthropic.com/v1/messages", timeout=30, headers={
            "x-api-key": settings.anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": settings.anthropic_model, "max_tokens": 400, "system": system_prompt(), "messages": hist})
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    except (httpx.HTTPError, ValueError):
        return {"reply": FALLBACK, "actions": ["call"]}
    reply, actions = split_actions(text)
    return {"reply": reply or FALLBACK, "actions": actions[:1]}
