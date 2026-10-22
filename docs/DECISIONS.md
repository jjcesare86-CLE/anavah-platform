# Decisions from Phillip (received Oct 22, 2026)

Each answer, what it means for the build, and what is still open. Items marked **DONE** are already in this repo.

## Decided

| # | Phillip's answer | What it means for the build |
|---|---|---|
| 1 | Clinical records are held in secure physical locations, encrypted data files and locked, secured computers, in line with HIPAA record requirements. | The website and back office hold **no clinical data**. They are not an EHR. Forms and Mia never ask for symptoms, diagnoses, medications. |
| 2 | The Protocol Generator is separate from the site, does not need to be built, and is the last priority. | **Out of scope.** Removed from nav. Parked in the backlog as its own future project. **DONE** (nav shows "Consultation Calls"). |
| 3 | Use Google Calendar for ALL patients and providers. It schedules an initial consultation; Phillip then schedules in Headway manually if needed. | Every "book" button points to the Google Calendar page (`config/practice.json` → `booking_url`). Built-in calendar is switched off (`BOOKING_MODE=google`) but kept in the code. Mia cannot book; she opens the scheduling page. **DONE** |
| 4 | Courses are in the pipeline but not ready; free for now. Skool will hold courses and also serve as the patient and provider anonymous community. | No store, no Stripe, no CE in Phase 1. Courses page = "coming soon" + Skool link. Community = Skool link (no custom community build). Skool is not a HIPAA-covered service, so community rules must ban health details. |
| 5 | Hero video: use "Nano Banana" to generate it. | Generate our own looping sunrise-in-clouds clip. No YouTube embed. See BUILD_SPEC "Hero video". |
| 6 | Booking: use Google Calendar. | Same as #3. |
| 7 | Contact: email Scherb@anavah-institute.org; **office (216) 625-0028; fax (216) 625-0053**; cell (330) 808-3383; LinkedIn, Headway, Skool links. | In `config/practice.json`. The old site and our first build showed 625-0053 as the phone; that is the fax. **DONE.** Cell is **not published** (see open item). |
| 8 | Clinical care limited to **Ohio and New York**. Provider services worldwide. | Stated on the home page, scheduling page, contact section, footer, terms and Mia. **DONE.** |
| 9 | BAAs: Phillip has one with Google Workspace; unsure if compliant. | Google Calendar scheduling stays. Supabase, Render, GHL, ElevenLabs and Anthropic have **no BAA**, so they must not receive patient identifiers or health details. The platform stores only contact-form leads and referral-partner prospects, and Mia/forms discourage health details. See "BAA actions" below. |
| 10 | Notice of Privacy Practices: needed if covered entity (answer pending). | A `/hipaa-notice` page is built as a draft, noindex, unlinked until counsel/EHR vendor supplies the final text. |
| 11 | Good Faith Estimate notice. | Short notice added to scheduling page and Terms. **DONE.** Counsel should compare it to the CMS model notice. |
| 12 | **Pricing will NOT be on the site.** Available after a consult call; sliding fee schedule. | No rates anywhere. The brief's private-pay rates are not used. "We offer private pay and insurance options; superbills available" stays, without numbers. |
| 13 | Crisis language on every page offering booking or chat. | Footer on every page, notice on contact form, scheduling page, Mia chat panel, Mia voice script. **DONE.** Add to the Skool About page and rules too. |
| 14 | Peptides and GLP-1s: educational mention only, with prescriber referral. No sourcing, dosing or compounding. | Disclaimer under appointments list. Mia refuses specifics. **DONE.** |

## BAA actions (for Phillip, not code)
- Google Workspace: confirm the BAA is accepted in the Admin console and that **Calendar appointment schedules** are covered in Google's current HIPAA services list. Until confirmed, the scheduling page asks only for name, email and phone.
- If Phillip wants Supabase, GHL, ElevenLabs or Anthropic to ever handle patient data, each needs its own HIPAA plan and BAA first.

## Follow-up answers (John, relayed from Phillip)
1. **Booking account:** Phillip.Scherbakov@gmail.com owns the Google Calendar page. Still to verify that the link in `practice.json` belongs to it and the appointment schedule asks only for name, email and phone.
2. **Consultation:** free for now. Site and Mia say "free initial consultation"; fees for ongoing care are discussed on that call. Revisit when this changes.
3. **Cell (330) 808-3383:** do not publish. Not on the site.
4. **Notice of Privacy Practices:** an interim version is on the unlinked, noindex `/hipaa-notice` page (effective Oct 22, 2026) under the Draft banner. Link it only after counsel or the records vendor approves; swap in their final text.
5. **Legal details (entity, address, governing law):** will come later.
6. **Peptide listings:** kept, with the educational disclaimer. Statistics: no primary source found for 68%, 1 in 3 or $935B, so they stay cut. `/about` instead cites Aaron et al. (2025), JAMA Network Open 8(3):e250268: about 39% depression and 40% anxiety symptoms among adults with chronic pain.
7. **Logo and photo:** already in the HTML.
8. **Skool:** linked from nav, footer, a home-page community band, `/community`, `/courses`, `/patients` and `/providers`.

## Still open
1. Verify the booking link belongs to Phillip.Scherbakov@gmail.com and the schedule's settings.
2. Records system (SimplePractice, other) and any patient portal URL (set `portal_url`).
3. Final Notice of Privacy Practices; counsel review of privacy and terms; entity name, mailing address, governing-law state.
4. Missing copy: "vetted network" criteria, "Anavah Play", a sentence on what Skool is for (a draft is on `/community`).
5. Skool setup: who moderates, and a pinned crisis-resources post.
6. IONOS password was shared in plain text in the brief: change it.
7. Phillip to approve softened wording and the unconfirmed provider offerings (shared protocols, vetted network, B2B subscriptions).
