"""Phase 1 site pages: routes, compliance rules from CLAUDE.md, crisis notice, no trackers, SEO basics."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PRACTICE = json.loads((ROOT / "config" / "practice.json").read_text(encoding="utf-8"))
DIMS = ["emotional", "physical", "social", "occupational", "environmental", "intellectual", "spiritual", "financial"]
NEW_PATHS = ["/patients", "/providers", "/about", "/courses", "/community", "/accessibility", "/hipaa-notice"] + [f"/wellness/{d}" for d in DIMS]
HTML = sorted(SITE.glob("*.html"))
# Text the public sees: built pages, their sources, Mia's knowledge, the site JS (Mia widget, forms)
SCANNED = HTML + sorted((ROOT / "site_src").glob("*.html")) + sorted((SITE / "assets").glob("*.js")) + [ROOT / "config" / "mia_knowledge.md", ROOT / "config" / "elevenlabs_agent.md", ROOT / "scripts" / "wellness_copy.py"]


def text(p):
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", NEW_PATHS)
def test_new_routes_serve(client, path):
    r = client.get(path)
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]


def test_hipaa_notice_is_draft_noindex_and_unlinked(client):
    r = client.get("/hipaa-notice")
    assert r.headers.get("x-robots-tag") == "noindex, nofollow"
    body = text(SITE / "hipaa-notice.html")
    assert 'content="noindex,nofollow"' in body and "Draft" in body and "draft-banner" in body
    assert "/hipaa-notice" not in text(SITE / "sitemap.xml")
    for p in HTML:
        if p.name != "hipaa-notice.html":
            assert "/hipaa-notice" not in text(p), f"{p.name} links the draft notice"


def test_sitemap_lists_indexable_pages_only():
    sm = text(SITE / "sitemap.xml")
    for path in ["/", "/patients", "/providers", "/about", "/courses", "/community", "/book", "/privacy", "/terms", "/accessibility"] + [f"/wellness/{d}" for d in DIMS]:
        assert f"<loc>https://anavah-institute.org{path}</loc>" in sm, path
    for path in ["/book-internal", "/manage", "/404", "/admin"]:
        assert path not in sm


@pytest.mark.parametrize("page", HTML, ids=lambda p: p.name)
def test_every_page_has_crisis_notice(page):
    t = text(page)
    assert "911" in t and "988" in t


def test_forms_carry_crisis_notice():
    for name in ["index.html", "about.html", "providers.html"]:
        t = text(SITE / name)
        form = t[t.index('id="contactForm"'):]
        assert "call 911" in form[:2500] and "988" in form[:2500], name


@pytest.mark.parametrize("page", SCANNED, ids=lambda p: p.name)
def test_banned_strings(page):
    t = text(page)
    assert not re.search(r"hipaa[- ]compliant", t, re.I)
    assert not re.search(r"\$\s?\d", t), "price or unsourced dollar figure"
    assert "pscherb@" not in t.lower()
    assert "Book a Session" not in t
    assert not re.search(r"CE credit|CEU|accredited|certified", t, re.I) or page.name in ("mia_knowledge.md", "elevenlabs_agent.md")
    for m in re.finditer(r"625-0053", t):
        ctx = t[max(0, m.start() - 120):m.end() + 5]
        assert re.search(r"fax", ctx, re.I), f"625-0053 outside a fax line in {page.name}: {ctx!r}"


def test_unsourced_stats_are_gone():
    for p in HTML:
        t = text(p)
        assert "68%" not in t and "1 in 3" not in t and "935" not in t, p.name


def test_no_trackers():
    bad = re.compile(r"googletagmanager|google-analytics|gtag\(|fbq\(|connect\.facebook|analytics\.js|hotjar|clarity\.ms|tiktok|segment\.com|plausible|matomo", re.I)
    for p in HTML + sorted((SITE / "assets").glob("*.js")):
        assert not bad.search(text(p)), p.name
    for p in HTML:
        for src in re.findall(r'<script[^>]+src="([^"]+)"', text(p)):
            assert src.startswith("/assets/"), f"{p.name} loads external script {src}"


@pytest.mark.parametrize("page", [p for p in HTML if p.name not in ("book-internal.html", "manage.html")], ids=lambda p: p.name)
def test_schedule_buttons_go_to_google_calendar(page):
    t = text(page)
    assert PRACTICE["booking_url"] in t
    for m in re.finditer(r'<a [^>]*href="([^"]+)"[^>]*>([^<]*(?:<span[^>]*>[^<]*</span>)?[^<]*)</a>', t):
        href, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if re.match(r"^(Schedule|Book)\b", label) and "Headway" not in label:
            assert href == PRACTICE["booking_url"] or href == "/book", f"{page.name}: '{label}' -> {href}"


@pytest.mark.parametrize("page", [p for p in HTML if p.name not in ("404.html",)], ids=lambda p: p.name)
def test_seo_basics(page):
    t = text(page)
    assert len(re.findall(r"<h1[ >]", t)) == 1
    assert re.search(r"<title>[^<]{10,}</title>", t) and 'name="description"' in t and 'rel="canonical"' in t
    for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        json.loads(blob)


def test_nav_and_footer_structure():
    t = text(SITE / "patients.html")
    nav = t[t.index('<nav class="site-nav"'):t.index("</nav>")]
    for label in ["Patients", "Professionals", "About", "Wellness", "Community", "Contact", "Schedule"]:
        assert label in nav
    assert nav.count("/wellness/") == 8 and PRACTICE["skool_url"] in nav and 'aria-current="page"' in nav


def test_patients_page_rules():
    t = text(SITE / "patients.html")
    assert "Ohio and New York" in t and "Medical and legal documentation services must occur during a session." in t
    assert "free initial consultation" in t and "free for now" in t
    assert "Patient portal" not in t, "portal link must stay hidden while portal_url is empty"


def test_providers_ce_item_rewritten_and_form_preselected():
    t = text(SITE / "providers.html")
    assert "Training and Lunch and Learns in integrative care coordination, with more courses on the way." in t
    assert '<option value="Healthcare Provider" selected>' in t


def test_wellness_pages_follow_spec():
    for d in DIMS:
        t = text(SITE / f"wellness-{d}.html")
        assert "Schedule a Consultation" in t and "Insurance-billed sessions" in t and PRACTICE["headway_url"] in t
        assert not re.search(r"(?<![A-Za-z])Body:", t)
        assert "removes cost as a barrier" not in t
    assert "Contact Us (employer inquiries)" in text(SITE / "wellness-occupational.html")
    assert "so there are no surprises" in text(SITE / "wellness-financial.html")


def test_courses_and_community_copy():
    assert "Courses are coming soon and will be free to start." in text(SITE / "courses.html")
    c = text(SITE / "community.html")
    assert "911" in c and "988" in c and "identifying health details" in c and PRACTICE["skool_url"] in c
