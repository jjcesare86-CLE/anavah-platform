# Anavah Institute — self-hosted website + booking + client back office

One Render service serves **everything**: the public website, the consultation scheduling page (which links to Google Calendar), the admin back office (`/admin`), the Mia chat/voice assistant backend, and the API. Data lives in **Supabase**; texts/emails go through **Go High Level**; Mia's voice runs on **ElevenLabs**. No WordPress, no IONOS hosting.

```
Visitors ─▶ Render (FastAPI) ─▶ Supabase Postgres (data) + Supabase Auth (admin login)
              │  ├─ /            public site (static, SEO'd)
              │  ├─ /book        live booking calendar        ├─▶ Go High Level (email + SMS + CRM contact sync)
              │  ├─ /manage      client cancel/reschedule     ├─▶ ElevenLabs (Mia voice) ─ tools ─▶ /api/agent/*
              │  ├─ /admin       Phillip's back office        └─▶ Anthropic (Mia text chat)
              └─ (reminder cron removed; add it back only with BOOKING_MODE=internal)
```

## What Phillip gets (/admin)
- **Dashboard** – today, next 7 days, new leads, counts
- **Calendar** (only when `BOOKING_MODE=internal`) – week view; click an appointment to reschedule / complete / no-show / cancel; add appointments by hand; time-off blocks
- **Clients** – CRM: contact info, status (lead/active/inactive/archived), tags, notes timeline, consent flags, appointment + message history, CSV export
- **Prospects** – referral partners (providers, PTs, PCPs, attorneys, orgs): pipeline status, CSV import
- **Outreach** – email/SMS campaigns from templates with merge fields, preview, dry-run; consent, unsubscribe, do-not-contact, daily cap built in
- **Message log** – every message with status
- **Settings** – weekly hours, visit types/durations/buffers, booking rules, GHL test + sync

**Scheduling:** everyone (patients and providers) books an *initial consultation* on Phillip's Google Calendar page; Phillip then schedules insurance-billed visits in Headway himself. The page URL lives in `config/practice.json`. The built-in calendar (visit types, availability, reminders) still exists but is off by default: set `BOOKING_MODE=internal` to turn it on (read the compliance notes first). Visitors also get a texting/voice assistant, Mia, who cannot book but opens the scheduling page.

**Start with `CLAUDE.md`, `docs/DECISIONS.md` and `docs/BUILD_SPEC.md`**: they hold Phillip's decisions and the build order.

---

# Setup walkthrough (about 60–90 minutes)

## 0. Before you start — decisions to confirm with Phillip
These are **placeholders in the build, not facts**: confirm them, then set them in /admin → Settings.
- [ ] The Google Calendar booking page is Phillip's, with real hours; it asks for name, email, phone only
- [ ] (Only if `BOOKING_MODE=internal`) real weekly hours, visit types, durations, buffers
- [ ] Practice **mailing address** (legally required in every marketing email → `BUSINESS_ADDRESS`). Also: is the Copley, OH address on his NPI record still in use, or Chelsea only?
- [ ] Legal entity name (e.g. "Anavah Institute LLC") for the footer/legal pages
- [ ] Late-cancel / no-show policy wording (Terms page)
- [ ] Insurance plans he actually accepts (site says "certain plans — contact us")
- [ ] Photo/bio approval; whether the nav logo is the circles mark or the triangle mark

## 1. GitHub
```bash
cd anavah-platform
git init && git add . && git commit -m "Anavah platform"
gh repo create jjcesare86-CLE/anavah-platform --private --source=. --push
```

## 2. Supabase (data + admin login)
1. supabase.com → **New project** (region: US East). Save the database password.
2. **SQL Editor → New query** → paste all of `supabase/schema.sql` → **Run**.
3. **Project Settings → Database → Connection string → Session pooler** → copy the URI → this is `DATABASE_URL`. (Use the *session pooler*, not the direct connection; it works from Render over IPv4.)
4. **Project Settings → API** → copy **Project URL** (`SUPABASE_URL`) and **anon public key** (`SUPABASE_ANON_KEY`).
5. **Authentication → Users → Add user → Create new user** for Phillip (email + strong password, check "Auto confirm"). Add one for yourself too.
6. **Authentication → Providers → Email**: turn **off** "Allow new users to sign up" so nobody else can create accounts. (The app *also* only lets emails in `ADMIN_EMAILS` into /admin.)
7. Consider enabling MFA for admin users (Authentication → MFA).

## 3. Render
1. Render → **New → Blueprint** → pick the repo (it reads `render.yaml`: one web service; `BOOKING_MODE=google` is preset. The reminder cron is only needed if you switch to `BOOKING_MODE=internal`, then re-add a cron service that runs `python -m app.jobs` every 15 minutes).
2. Fill the prompted env vars (see `.env.example` for each). Minimum to go live: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `ADMIN_EMAILS`. Also set `BUSINESS_ADDRESS` (needed for email marketing) and keep `OUTREACH_DRY_RUN=true` until tested.
3. Deploy. Open `https://<service>.onrender.com/` and `/admin`; sign in as Phillip. The first start auto-creates starter visit types and hours.
4. **Custom domain**: Render → web service → Settings → Custom Domains → add `anavah-institute.org` and `www`. At the domain registrar (where DNS lives; since the client left IONOS hosting, make sure the domain itself is still registered and renewed) set the records Render shows. **Do not delete existing MX/TXT records** if email for `@anavah-institute.org` runs on the same domain. Set `SITE_URL=https://anavah-institute.org`, then rebuild the static pages' canonical URLs: `python scripts/build_site.py https://anavah-institute.org` and commit.
5. Use at least the **Starter** plan (free web services sleep, which makes booking slow and breaks cron/webhooks).

## 4. Go High Level (email + SMS + CRM)
1. **Settings → Private Integrations → Create** with scopes: contacts (read/write), conversations (read), conversations/messages (write), locations (read). Copy the token → `GHL_TOKEN`. Copy your Location ID (Settings → Business Profile) → `GHL_LOCATION_ID`.
2. Set up a **sending domain** for email (Settings → Email Services) so mail comes from the practice's domain and passes SPF/DKIM — otherwise it lands in spam.
3. For **SMS in the US you must complete A2P 10DLC registration** in GHL (takes days). Until then SMS will fail; email still works.
4. In /admin → **Settings → Test GHL connection**. Then **Sync clients to GHL** to push existing clients into GHL as contacts.
5. Keep `OUTREACH_DRY_RUN=true` until you've sent yourself a test booking confirmation; then set it to `false` in Render.
6. GHL API note: endpoint paths/`Version` headers are in `app/ghl.py`; if GHL returns an error, the exact message shows in the Message log.

## 5. Mia — text chat (Anthropic)
Set `ANTHROPIC_API_KEY` (console.anthropic.com). Without it Mia replies with a polite "call the office" fallback. Her knowledge lives in `config/mia_knowledge.md` — edit, commit, redeploy. She only states facts written there.

## 6. Mia — voice (ElevenLabs)
Run `python scripts/create_elevenlabs_agent.py` (see top of the file; or follow `config/elevenlabs_agent.md` by hand). Pick a **warm, calm voice** from the Voice Library and set `ELEVENLABS_VOICE_ID`. Put `ELEVENLABS_API_KEY` + `ELEVENLABS_AGENT_ID` in Render. In the agent's Security settings enable authentication + domain allowlist. The same `AGENT_WEBHOOK_SECRET` must be in Render and in the agent tools.

## 7. Go-live checklist
- [ ] `/book` opens the Google Calendar page; a test consultation appears on Phillip's calendar
- [ ] Contact form submission shows up under Clients as a lead
- [ ] Mia text + voice tested on phone and desktop (voice needs HTTPS + mic permission)
- [ ] Privacy + Terms reviewed by counsel, then remove the yellow "Draft" banner from `site_src/privacy.body.html` and `terms.body.html` and re-run `scripts/build_site.py`
- [ ] `BUSINESS_ADDRESS` set; `OUTREACH_DRY_RUN=false`
- [ ] Google Search Console: add the domain, submit `/sitemap.xml`
- [ ] Old WordPress/IONOS site 301-redirects or is retired (avoid duplicate content)

---

# Compliance — read this
This is a scheduling + CRM system, **not an EHR**. Do not store clinical notes, diagnoses, or medications in it; the notes fields say so, and Mia is instructed to refuse health details.
- **HIPAA**: if Phillip is a covered entity, any vendor that handles patient identifiers needs a **BAA**: Supabase, Render, Go High Level, ElevenLabs and Anthropic. Each vendor has its own HIPAA-eligible plan/BAA process (usually a higher tier) — ask each one and confirm current terms before real patient data flows. Appointment times + names + "psychiatric intake" can be PHI. Get counsel's/compliance advice **before** real patient data flows. The site intentionally makes **no "HIPAA-compliant" claim**. Phillip has a BAA with Google Workspace only; none of the vendors above has a BAA today, so none may receive patient identifiers or health details (contact forms and Mia ask people not to share any).
- **Email (CAN-SPAM)**: unsubscribe link + mailing address on every outreach email — enforced; no sends without `BUSINESS_ADDRESS`.
- **SMS (TCPA)**: texts go only to clients with recorded `sms_consent`; prospects can't be texted; every outreach text ends with STOP language; GHL handles STOP replies (also confirm that in GHL).
- Outreach to patients requires their `email_consent` flag (booking does **not** grant marketing consent). Appointment confirmations/reminders are transactional.
- Rate limits + honeypots protect forms; admin routes require a Supabase-verified login on the allowlist; the database blocks double-booking at the constraint level (verified against real Postgres, including a 6-way concurrent race).

# Development
```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
# export the variables from .env.example you need (the app reads real environment variables, not a .env file).
# With no DATABASE_URL it uses a local SQLite file.
DEV_ADMIN_TOKEN=dev uvicorn app.main:app --reload   # admin: sessionStorage anv_tok="dev" (dev only; ignored when SUPABASE_URL is set)
pip install pytest && pytest                          # 23 tests
python scripts/build_site.py https://anavah-institute.org   # regenerate site/*.html from site_src/
```
Layout: `app/` API · `site/` + `site_src/` public pages · `admin/` back-office SPA · `supabase/schema.sql` · `config/mia_knowledge.md` · `scripts/` · `tests/`.

# Not included (ideas for next)
Payments/deposits (Stripe), Google/Outlook calendar two-way sync, video-visit links (add a Zoom/Doxy link per visit type), intake forms/e-signature, inbound-reply inbox (GHL Conversations already shows replies), recurring appointments, multi-clinician scheduling, waitlist, referral-source reporting.
