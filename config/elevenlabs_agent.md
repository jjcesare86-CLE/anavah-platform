# Mia voice agent — manual setup (if you'd rather not run the script)

In ElevenLabs: **Agents → Create agent → Blank.**

1. **Voice**: pick a warm, calm, unhurried voice from the Voice Library (try "gentle", "calm", "warm" in the filters; audition with: "Hello, this is Mia from Anavah Institute. Take all the time you need.").
2. **First message**: `Hello, this is Mia, the virtual assistant for Anavah Institute. How can I help you today?`
3. **System prompt**: run `python scripts/create_elevenlabs_agent.py --print-prompt` and paste the output (it is `mia_knowledge.md` + voice rules).
4. **Tools** — add each:

| Name | Type | Details |
|---|---|---|
| request_callback | Server (webhook) | POST `/api/agent/callback`, same header, body: `first_name` (required), `last_name`, `phone`, `email`, `reason` |
| navigate_to | Client | param `section` (string): top, mission, services, about, appointments, insurance, contact |
| open_booking | Client | no params; opens the consultation scheduling page |

5. **Security**: enable authentication (so the site uses signed URLs from the backend) and add your domain to the allowlist.
6. Copy the **Agent ID** into Render as `ELEVENLABS_AGENT_ID` (and your API key as `ELEVENLABS_API_KEY`).
7. Test in the ElevenLabs "Test agent" panel: ask to schedule a consultation (it should open the scheduling page and NOT try to book), and ask for a callback; check the callback appears in /admin.

Healthcare note: Mia must never collect health details. Zero-retention mode and a BAA are available on ElevenLabs Enterprise — ask them before the voice agent speaks with real patients.
