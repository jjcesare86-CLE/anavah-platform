# Anavah Institute — project instructions for Claude Code

Website + lightweight back office for Anavah Institute (Phillip Scherbakov, PMHNP; integrative psychiatry + provider education; Chelsea, Manhattan NY). Owner of this repo: John (Automation Nation). Client contact: Phillip.

## Read first
1. `docs/DECISIONS.md` — Phillip's answers (Oct 22 2026). These win over everything else.
2. `docs/BUILD_SPEC.md` — what to build, in order, with acceptance checks.
3. `docs/SOURCE_BRIEF.md` — Phillip's original copy and requirements (credentials removed). Use it for page copy. Where it conflicts with DECISIONS.md, DECISIONS.md wins.
4. `README.md` — deploy walkthrough (Supabase, Render, GHL, ElevenLabs).

## Stack and layout
FastAPI on Render serves static pages, API, admin SPA. Supabase Postgres + Auth. GHL for email/SMS. ElevenLabs voice + Anthropic text for the Mia assistant.
- `config/practice.json` — single source for phone, fax, email, location, Google booking URL, Headway, Skool, LinkedIn. Never hard-code these in pages; use `{{PLACEHOLDERS}}` in `site_src/*.body.html` (see `subst()` in `scripts/build_site.py`).
- `site_src/*.body.html` → `python scripts/build_site.py https://anavah-institute.org` → `site/*.html` (commit the output).
- `site/assets/` JS/CSS/images. Style: navy/gold/sage, Cormorant Garamond + DM Sans, animated clouds hero, orb, 3D-tilt service figures. Keep it.
- `config/mia_knowledge.md` — Mia's only source of facts. Keep in sync with site copy.
- `app/` API. `BOOKING_MODE=google` (default) disables the built-in calendar; do not delete that code.
- `.venv/bin/python -m pytest -q` must pass before every commit.

## Hard rules (compliance and trust)
- Scheduling = Google Calendar link only (`booking_url`). Insurance-billed visits are scheduled by Phillip in Headway after the consultation. No other booking UI.
- No prices anywhere on the site, in Mia, or in emails. Fees are discussed on the consultation call (sliding fee schedule).
- Never write "HIPAA-compliant" (or similar) anywhere. Describe what we do, not a certification.
- No clinical or health information collected on the site: forms and Mia must not ask for symptoms, diagnoses, medications, DOB, insurance IDs. Every form/chat/booking page carries the "not for emergencies: 911 / 988" notice.
- Clinical care only for patients in Ohio and New York. Provider services worldwide. Say so wherever booking is offered.
- Peptides, GLP-1s, supplements, medications: educational mention only, "discuss with a licensed prescriber". No dosing, sourcing, compounding, or "get it from" content.
- No CE credits, "certified", or "accredited" claims for courses. Courses are free and "coming soon" for now.
- No ad/analytics trackers (no Meta Pixel, GA4, TikTok) on any page. If analytics are wanted later, cookieless and not on booking/contact pages.
- Statistics need a primary source cited on the page or they do not ship (68%, 1 in 3, $935B are unsourced).
- Fax is (216) 625-0053. Office phone is (216) 625-0028. Do not mix them up (the old site had the fax listed as the phone).
- Never commit credentials. Phillip's IONOS password was pasted in the original brief and must be treated as exposed.
- Legal pages stay behind the yellow "Draft — pending legal review" banner until Phillip's counsel approves.
