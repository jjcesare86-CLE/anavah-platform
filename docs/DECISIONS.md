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

## Still open (blocking or nearly)
1. **Which Google account owns the booking page?** Phillip's message was cut off after "assuming that my google account is…". The build uses the calendar link already in the v1.3 sample: `https://calendar.app.google/WhZgHS8WDVCT1ZDKA`. Confirm it is his and that the appointment schedule is set up the way he wants (duration, availability, questions limited to name/email/phone).
2. **Is the consultation free?** The brief says "free consultation call"; his answer says fees come after the consult. The site says "initial consultation" and does not say "free" until he confirms.
3. **Cell (330) 808-3383:** publish it, or keep it for internal use only? Default: not published.
4. **Notice of Privacy Practices:** does he have one? Which EHR/billing system is the record system (SimplePractice, other)? Which patient portal, if any, should the "Patient portal" link go to?
5. **Legal:** entity name, mailing address (needed for email marketing), governing-law state (the brief's Ohio + AAA clause vs a NY practice), counsel review of privacy/terms.
6. **Peptide listings:** the original copy lists "Peptide therapy" and "Peptide Integrations". Kept for now with the educational disclaimer; Phillip decides whether to keep them as listed services.
7. **Statistics (68%, 1 in 3, $935B):** need sources or they are cut.
8. **Missing copy:** "Who joins", provider/B2B tiers (not needed while courses are free), "vetted network" criteria, "Anavah Play", a sentence on what Skool is for.
9. **Assets:** logo file (circles vs triangle mark), Phillip's approved photo and bio with rights confirmed, "ALL CLINICAL FORMS" content (the brief's link could not be opened).
10. **Skool setup:** who moderates, and a pinned crisis-resources post.
11. **IONOS password** was shared in plain text in the brief: change it.
