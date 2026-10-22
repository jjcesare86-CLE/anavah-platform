# Build spec for Claude Code

Work through the phases in order. After each phase: run `.venv/bin/python scripts/build_site.py https://anavah-institute.org`, run `.venv/bin/python -m pytest -q`, and check the pages in a browser at desktop and phone width. Rules in `CLAUDE.md` apply to everything.

## Where things stand
Done in this repo: home page matches sample v1.3; all booking goes to Google Calendar; practice facts in `config/practice.json`; Ohio/New York statement; crisis notices; no pricing; Mia and voice script updated; legal pages reworded (still draft); 28 tests pass.
Built but dormant: Supabase booking calendar (`BOOKING_MODE=internal`), admin back office at `/admin` (leads from the contact form, referral-partner prospects, outreach with consent guard rails).

## Phase 1 — Site structure and copy (the main job)
Use copy from `docs/SOURCE_BRIEF.md`. Generate every page through `site_src/*.body.html` + `scripts/build_site.py` (add pages to `PAGES`, sitemap, nav, footer). Same visual system as the home page.

**Navigation.** Patients · Professionals · About · Wellness (dropdown of the 8 dimensions) · Community (→ Skool, new tab) · Contact · "Schedule" button (Google Calendar, new tab). Update the home page nav links from `#anchors` to the new pages once they exist.

**Pages**
| Path | Content |
|---|---|
| `/patients` | Brief's "For Patients" text. The 4-step list. Services list from the brief's "Psychiatric Services" section (trim anything Phillip has not confirmed; see note). Billing sentence without numbers: private pay and insurance options; superbills for out-of-network reimbursement; fees discussed on the consultation call. "Medical and legal documentation services must occur during a session." Region note (Ohio and New York). Intake forms: "provided after your consultation through our secure system" (no PDFs with PHI on the site). Patient portal link only if `portal_url` is set in `practice.json` (add the key; hide the link when empty). Community → Skool. CTA → Google Calendar. |
| `/providers` | "Why partner" six items. **Rewrite the CE item** to: "Training and Lunch and Learns in integrative care coordination, with more courses on the way." No "earn CE credits". "Who joins" with the draft in `docs/COPY_DRAFTS.md`. Lunch-and-Learn and network sign-up → Google Calendar consultation or the contact form with "Healthcare Provider" selected. Courses → `/courses`. Consulting and B2B: describe, no prices. |
| `/about` | Anavah = Hebrew for humility; founding principle; eight dimensions; mission; the problem section (stats only with sources); the Anavah model (Mind, Body, Coordination — reuse the orb copy); leadership (Phillip, existing bio + photo); contact. |
| `/wellness/<dimension>` ×8 | Emotional, Physical, Social, Occupational, Environmental, Intellectual, Spiritual, Financial. One shared template: headline, sub-headline, "What is X wellness?", "How Anavah supports X wellness", bullet list, CTA. Copy is in the brief. Fixes: replace every "Book a Session on Headway" button with "Schedule a Consultation" (Google Calendar) plus a small "Insurance-billed sessions: Headway" link. **Financial:** delete "removes cost as a barrier"; use the second-level draft in `docs/COPY_DRAFTS.md`. Occupational keeps the second button "Contact Us (employer inquiries)". Remove the stray "Body:" labels that appear in the brief copy (Environmental, Spiritual, Financial). |
| `/courses` | "Courses are coming soon and will be free to start. Join the community to be first to know." Skool link. No store, no prices, no CE language. |
| `/community` | 302 to Skool, or a short page that explains Skool, the community rules (no health details; not for emergencies; 911/988), then the link. Prefer the short page. |
| `/privacy`, `/terms` | Already reworded. Keep the Draft banner. |
| `/hipaa-notice` | Draft Notice of Privacy Practices from the brief, with a Draft banner and `noindex`. Do **not** link it from the footer until counsel approves. Contact = `{{EMAIL}}`, `{{PHONE}}` (not the old pscherb@ address or fax-as-phone). |
| `/accessibility` | Short statement: aim for WCAG 2.1 AA, how to report problems (email). |

**Copy rules while building:** keep Phillip's wording where it is safe; fix claims listed in `CLAUDE.md`; single canonical email `{{EMAIL}}`; no "HIPAA-compliant"; no outcome promises; no testimonials.

**Services note.** The brief's "Psychiatric Services (PMHNP scope)" lists therapies and specialty care (CBT/ACT, trauma-informed care, TRD strategies, tapering, supplement protocols, gut-brain, hormonal) and "Bibliotherapy - publishing your memoir". Show them as the brief lists them, but phrase supplements/peptides as "education and discussion with a prescriber". Flag to Phillip anything that reads like a promise of treatment.

## Phase 2 — Hero video
Replace the CSS cloud background with video, keeping the cloud animation as the fallback and the poster.
- Generate with Nano Banana (image) then animate to video (the Higgsfield connector in Claude can do both; ask John to approve credit use). Prompt: *"Soft golden sunrise breaking through layered clouds, warm light rays, slow drifting movement, calm and spacious, no people, no text, photorealistic, seamless loop, 16:9."* 6–10 s, 1080p.
- Deliver: `site/assets/img/hero.mp4` (H.264, ≤3 MB, no audio), `hero.webm`, `hero-poster.jpg`.
- HTML: `<video autoplay muted loop playsinline preload="metadata" poster=...>`; hide the video and show the poster when `prefers-reduced-motion` is set or on slow connections (`navigator.connection.saveData`). Keep text contrast AA over the video (dark navy gradient overlay).
- Test: Lighthouse performance not worse than the current build; hero text readable on phone.

## Phase 3 — Polish and launch checks
- Accessibility pass: keyboard nav, focus states, contrast, alt text, labels, reduced motion.
- SEO: per-page title/description, JSON-LD (already on home), sitemap, canonical URLs. Add `FAQPage` JSON-LD only if the FAQ is real content.
- Crisis notice present on every page (footer) and every form.
- Search the repo for banned strings: `HIPAA-compliant`, `$` followed by digits, `625-0053` outside the fax line, `pscherb@`, `Headway` buttons labelled "Book a Session", `CE credit`.
- Deploy per README. Set `BOOKING_MODE=google` (default), `BUSINESS_ADDRESS`, keep `OUTREACH_DRY_RUN=true` until tested.

## Later (not now)
- Protocol Generator: separate project, last priority. If built: practitioner-only, server-side AI calls, no patient names, citations verified (Crossref/PubMed), peptide content educational only.
- Courses and store: build in Skool first. Add Stripe and a store only when courses are ready and Phillip wants to charge. Do not label anything CE-accredited until an approved CE provider agrees in writing.
- Provider subscriptions / B2B tiers: need Phillip's tiers and prices first.
- Turning the internal calendar back on: set `BOOKING_MODE=internal`; requires BAAs for Supabase, Render and GHL first.
- Patient portal: link to the EHR vendor's portal; do not build one.

## Course development advice (for Phillip)
1. Start with one 60–90 minute recorded Lunch and Learn; that becomes Course #1.
2. Outline in 5 modules: learning goal, 10–15 minute video, one-page handout, 5-question quiz each.
3. Host in the Skool Classroom (free for now); add a paywall later if wanted.
4. Give a "certificate of completion", not a "certification"; CE credit only after an approved CE provider accredits it.
5. Claude can draft outlines, scripts, slide decks, quizzes and workbooks for each module.
