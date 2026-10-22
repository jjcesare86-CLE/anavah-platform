"""Generates site/*.html from site_src/*.body.html with a shared head, nav, footer, and Mia widget.

Usage: python scripts/build_site.py [https://your-domain]
Output is committed, so Render does not need to run this.
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wellness_copy import WELLNESS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "site_src", ROOT / "site"
PRACTICE = json.loads((ROOT / "config" / "practice.json").read_text(encoding="utf-8"))
BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://anavah-institute.org").rstrip("/")

DIMS = [
    ("Emotional", "Coping effectively with life and creating satisfying relationships", "#D4B581"),
    ("Financial", "Satisfaction with current and future financial situations", "#8A9A7B"),
    ("Social", "Developing a sense of connection, belonging, and a well-developed support system", "#B8924A"),
    ("Spiritual", "Expanding our sense of purpose and meaning in life", "#C5CFB8"),
    ("Occupational", "Personal satisfaction and enrichment derived from one's work", "#E8D5A8"),
    ("Physical", "Recognizing the need for physical activity, diet, sleep and nutrition", "#8A9A7B"),
    ("Intellectual", "Recognizing creative abilities and finding ways to expand knowledge and skills", "#D4B581"),
    ("Environmental", "Good health by occupying pleasant, stimulating environments that support well-being", "#B8924A"),
]


def esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def wheel():
    out = ['          <g class="wheel">']
    for i, (n, d, c) in enumerate(DIMS):
        a = math.radians(-90 + i * 45)
        cx, cy = 250 + math.cos(a) * 85, 250 + math.sin(a) * 85
        out.append(f'          <circle class="petal" cx="{cx:.1f}" cy="{cy:.1f}" r="95" fill="{c}" fill-opacity=".55" stroke="#fff" stroke-width="1.5"><title>{esc(n)} — {esc(d)}</title></circle>')
    out.append("          </g>")
    for i, (n, d, c) in enumerate(DIMS):
        a = math.radians(-90 + i * 45)
        lx, ly = 250 + math.cos(a) * 205, 250 + math.sin(a) * 205
        anchor = "middle" if abs(math.cos(a)) < .3 else ("start" if math.cos(a) > 0 else "end")
        out.append(f'          <text class="dim-label" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}">{n}</text>')
    return "\n".join(out)


JSONLD = {
    "@context": "https://schema.org",
    "@type": ["MedicalBusiness", "LocalBusiness"],
    "name": "Anavah Institute",
    "slogan": "Empowering Radical Responsibility",
    "description": "Integrative healthcare organization in Chelsea, Manhattan bridging mental health and physical medicine: psychiatric services, exercise screening, nutritional consultation, integrative blood work and care coordination.",
    "url": BASE + "/",
    "image": BASE + "/assets/img/hero-clouds.jpg",
    "logo": BASE + "/assets/img/logo.png",
    "telephone": "+1-" + PRACTICE["phone_href"][2:5] + "-" + PRACTICE["phone_href"][5:8] + "-" + PRACTICE["phone_href"][8:],
    "faxNumber": "+1-" + re.sub(r"\D", "", PRACTICE["fax"])[:3] + "-" + re.sub(r"\D", "", PRACTICE["fax"])[3:6] + "-" + re.sub(r"\D", "", PRACTICE["fax"])[6:],
    "email": PRACTICE["email"],
    "sameAs": [PRACTICE["linkedin_url"], PRACTICE["headway_url"], PRACTICE["skool_url"]],
    "address": {"@type": "PostalAddress", "addressLocality": "New York", "addressRegion": "NY", "addressCountry": "US"},
    "areaServed": [{"@type": "State", "name": "New York"}, {"@type": "State", "name": "Ohio"}],
    "medicalSpecialty": "Psychiatric",
    "founder": {"@type": "Person", "name": "Phillip Scherbakov", "jobTitle": "Psychiatric Nurse Practitioner (PMHNP)"},
    "potentialAction": {"@type": "ReserveAction", "target": PRACTICE["booking_url"], "name": "Schedule a Consultation"},
}

def _dd_links():
    return "".join(f'<li><a href="/wellness/{d["slug"]}" data-p="/wellness/{d["slug"]}">{d["name"]}</a></li>' for d in WELLNESS)


NAV = """<a class="skip" href="#main">Skip to content</a>
<nav class="site-nav" id="nav" aria-label="Main">
  <div class="container nav-inner">
    <a href="/" class="site-logo"><span class="logo-mark"></span>Anavah<span class="tag">Institute</span></a>
    <ul class="nav-menu" id="navMenu">
      <li><a href="/patients" data-p="/patients">Patients</a></li>
      <li><a href="/providers" data-p="/providers">Professionals</a></li>
      <li><a href="/about" data-p="/about">About</a></li>
      <li class="has-sub"><a href="/about#dimensions" aria-haspopup="true">Wellness</a>
        <ul class="sub-menu">""" + _dd_links() + """</ul></li>
      <li><a href="{{SKOOL_URL}}" target="_blank" rel="noopener">Community</a></li>
      <li><a href="/#contact">Contact</a></li>
    </ul>
    <a href="{{BOOKING_URL}}" target="_blank" rel="noopener" class="btn btn-gold btn-sm nav-cta">Schedule <span class="arrow">→</span></a>
    <button class="mobile-toggle" aria-label="Menu" aria-controls="navMenu" onclick="document.getElementById('navMenu').classList.toggle('open')"><span></span><span></span><span></span></button>
  </div>
</nav>"""

FOOTER = """<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div>
        <a href="/" class="site-logo"><span class="logo-mark"></span>Anavah<span class="tag">Institute</span></a>
        <p class="footer-blurb">The connective tissue between mental health and physical medicine. Integrative care, coordinated.<br>Chelsea, Manhattan, New York, NY, USA<br>Clinical care in Ohio and New York &middot; Provider services worldwide</p>
        <div class="contact-line"><a href="mailto:{{EMAIL}}">{{EMAIL}}</a><a href="tel:+{{PHONE_HREF}}">{{PHONE}}</a><span>Fax {{FAX}}</span></div>
      </div>
      <div class="footer-col"><h6>Patients</h6><ul><li><a href="/patients">For Patients</a></li><li><a href="{{BOOKING_URL}}" target="_blank" rel="noopener">Schedule a Consultation</a></li><li><a href="{{HEADWAY_URL}}" target="_blank" rel="noopener">Headway profile</a></li><li><a href="/community">Community</a></li><li><a href="/courses">Courses</a></li></ul></div>
      <div class="footer-col"><h6>Professionals</h6><ul><li><a href="/providers">For Professionals</a></li><li><a href="/providers#contact">Lunch and Learns</a></li><li><a href="{{BOOKING_URL}}" target="_blank" rel="noopener">Consultation Calls</a></li><li><a href="{{SKOOL_URL}}" target="_blank" rel="noopener">Clinician community</a></li></ul></div>
      <div class="footer-col"><h6>Institute</h6><ul><li><a href="/about">About</a></li><li><a href="/about#leadership">About Phillip</a></li><li><a href="/about#dimensions">Eight dimensions of wellness</a></li><li><a href="/#contact">Contact</a></li><li><a href="{{LINKEDIN_URL}}" target="_blank" rel="noopener">LinkedIn</a></li><li><a href="/accessibility">Accessibility</a></li><li><a href="/terms">Terms and Conditions</a></li><li><a href="/privacy">Privacy Policy</a></li></ul></div>
    </div>
    <div class="footer-bottom">
      <span>Copyright &copy; 2026 Anavah Institute - All Rights Reserved.</span>
      <span>In an emergency call 911 &middot; Crisis support: call or text 988</span>
    </div>
  </div>
</footer>"""

CRISIS_NOTE = '<p class="crisis-note"><strong>This page is not for emergencies.</strong> If you are in immediate danger, call 911. For crisis support, call or text the 988 Suicide and Crisis Lifeline.</p>'
REGION_NOTE = '<p class="region-note">Clinical care is limited to <strong>{{STATES}}</strong>. Provider services are available worldwide. Fees are discussed on your consultation call.</p>'


def h(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wellness_body(d, n):
    items = []
    for lead, rest in d["items"]:
        if d.get("plain_items"):
            items.append(f'<p><strong>{h(lead)}</strong> {h(rest)}</p>')
        else:
            items.append(f'<li><strong>{h(lead)}</strong> &mdash; {h(rest)}</li>')
    listing = "".join(items) if d.get("plain_items") else '<ul class="pg-list big">' + "".join(items) + "</ul>"
    what = "".join(f"<p>{h(t)}</p>" for t in d["what"])
    extra = ""
    if d.get("extra"):
        extra = f'<a href="{d["extra"][1]}" class="btn btn-ghost">{h(d["extra"][0])}</a>'
    community = ""
    if d.get("community"):
        community = '<p style="margin-top:22px"><a class="btn btn-ghost" href="{{SKOOL_URL}}" target="_blank" rel="noopener">Join the community <span class="arrow">→</span></a></p>'
    prev_d, next_d = WELLNESS[(n - 1) % 8], WELLNESS[(n + 1) % 8]
    cur = ' aria-current="page"'
    others = " ".join(f'<a href="/wellness/{o["slug"]}"{cur if o is d else ""}>{o["name"]}</a>' for o in WELLNESS)
    return f"""<main id="main">
<header class="page-hero">
  <div class="container"><div class="page-hero-inner">
    <span class="hero-eyebrow label">{d["name"]} Wellness &middot; Dimension {n + 1} of 8</span>
    <h1>{h(d["headline"])}</h1>
    <p class="sub">{h(d["sub"])}</p>
  </div></div>
</header>
<section class="pg-section">
  <div class="container pg-narrow reveal">
    <h2 class="pg-h2">What is {d["name"].lower()} wellness?</h2>
    {what}
  </div>
</section>
<section class="pg-section alt">
  <div class="container pg-narrow reveal">
    <h2 class="pg-h2">How Anavah supports {d["name"].lower()} wellness.</h2>
    <p>{h(d["how_intro"])}</p>
    {listing}
    {community}
  </div>
</section>
<section class="pg-cta">
  <div class="container reveal">
    <h2>Start with a <em>consultation.</em></h2>
    <p style="display:flex;gap:14px;flex-wrap:wrap;justify-content:center"><a href="{{{{BOOKING_URL}}}}" target="_blank" rel="noopener" class="btn btn-gold">Schedule a Consultation <span class="arrow">→</span></a>{extra}</p>
    <p class="muted small">Insurance-billed sessions: <a href="{{{{HEADWAY_URL}}}}" target="_blank" rel="noopener">Headway</a></p>
    {{{{REGION_NOTE}}}}
    {{{{CRISIS_NOTE}}}}
  </div>
</section>
<nav class="wellness-links" aria-label="The eight dimensions of wellness">
  <div class="container">
    <span class="label">The eight dimensions</span>
    <p>{others}</p>
    <p class="wl-step"><a href="/wellness/{prev_d["slug"]}">&larr; {prev_d["name"]}</a><a href="/wellness/{next_d["slug"]}">{next_d["name"]} &rarr;</a></p>
  </div>
</nav>
</main>
"""


PAGES = [
    dict(file="index.html", path="/", body="index", index=True,
         title="Anavah Institute | Integrative Psychiatry & Care Coordination in Chelsea, Manhattan",
         desc="Anavah Institute, led by Phillip Scherbakov, PMHNP, bridges mental health and physical medicine in Chelsea, Manhattan: psychiatric care, nutrition, exercise screening, integrative blood work and care coordination.",
         scripts=["main.js", "orb.js", "contact.js"], ld=True),
    dict(file="patients.html", path="/patients", body="patients", index=True, crumb="For Patients",
         title="For Patients | Integrative Psychiatric Care | Anavah Institute",
         desc="Integrative psychiatric care in Ohio and New York with Phillip Scherbakov, PMHNP. How to get started, services, private pay and insurance options. Begin with an initial consultation.",
         scripts=["main.js"]),
    dict(file="providers.html", path="/providers", body="providers", index=True, crumb="For Professionals",
         title="For Healthcare Professionals | Anavah Institute",
         desc="Education, consulting and a cross-disciplinary network for clinicians and healthcare organizations. Lunch and Learns, training and care-coordination support, available worldwide.",
         scripts=["main.js", "contact.js"]),
    dict(file="about.html", path="/about", body="about", index=True, crumb="About",
         title="About Anavah Institute | Radical Responsibility and the Eight Dimensions of Wellness",
         desc="Anavah is the Hebrew word for humility. Learn about our founding principle, the eight dimensions of wellness, the Anavah model of mind, body and coordination, and our founder Phillip Scherbakov, PMHNP.",
         scripts=["main.js", "contact.js"]),
] + [
    dict(file=f"wellness-{d['slug']}.html", path=f"/wellness/{d['slug']}", body="wellness", html=wellness_body(d, i), index=True,
         crumb=f"{d['name']} Wellness",
         title=f"{d['name']} Wellness | Anavah Institute",
         desc=f"What {d['name'].lower()} wellness is, and how Anavah Institute supports it as one of the eight dimensions of wellness.",
         scripts=["main.js"])
    for i, d in enumerate(WELLNESS)
] + [
    dict(file="courses.html", path="/courses", body="courses", index=True, crumb="Courses",
         title="Courses | Coming Soon | Anavah Institute",
         desc="Anavah Institute courses are coming soon and will be free to start. Join the community to be the first to know.",
         scripts=["main.js"]),
    dict(file="community.html", path="/community", body="community", index=True, crumb="Community",
         title="Community | Anavah Institute",
         desc="Anavah's peer community on Skool: connection and education for patients and healthcare providers. Community rules and how to join.",
         scripts=["main.js"]),
    dict(file="book.html", path="/book", body="book", index=True, crumb="Schedule",
         title="Schedule an Initial Consultation | Anavah Institute",
         desc="Schedule an initial consultation with Anavah Institute. Patients and healthcare providers both start here. Clinical care in Ohio and New York; provider services worldwide.",
         scripts=["main.js"]),
    dict(file="book-internal.html", path="/book-internal", body="book-internal", index=False,
         title="Book an Appointment | Anavah Institute", desc="Book an appointment with Anavah Institute.",
         scripts=["main.js", "booking.js"]),
    dict(file="manage.html", path="/manage", body="manage", index=False,
         title="Manage Your Appointment | Anavah Institute", desc="Change or cancel your Anavah Institute appointment.",
         scripts=["main.js", "booking.js"]),
    dict(file="privacy.html", path="/privacy", body="privacy", index=True, crumb="Privacy Policy",
         title="Privacy Policy | Anavah Institute", desc="How Anavah Institute collects, uses and protects information on this website.",
         scripts=["main.js"]),
    dict(file="terms.html", path="/terms", body="terms", index=True, crumb="Terms and Conditions",
         title="Terms and Conditions | Anavah Institute", desc="Terms of use for the Anavah Institute website and online booking.",
         scripts=["main.js"]),
    dict(file="accessibility.html", path="/accessibility", body="accessibility", index=True, crumb="Accessibility",
         title="Accessibility Statement | Anavah Institute",
         desc="Anavah Institute aims to meet WCAG 2.1 AA. Learn what we do and how to report an accessibility problem.",
         scripts=["main.js"]),
    # Draft: noindex, not linked from the footer or nav, and not in the sitemap until counsel approves.
    dict(file="hipaa-notice.html", path="/hipaa-notice", body="hipaa-notice", index=False,
         title="Notice of Privacy Practices (Draft) | Anavah Institute", desc="Draft notice of privacy practices.",
         scripts=["main.js"]),
    dict(file="404.html", path="/404", body="404", index=False,
         title="Page not found | Anavah Institute", desc="Page not found.", scripts=["main.js"]),
]


def subst(html):
    pairs = {"BOOKING_URL": PRACTICE["booking_url"], "HEADWAY_URL": PRACTICE["headway_url"], "SKOOL_URL": PRACTICE["skool_url"],
             "LINKEDIN_URL": PRACTICE["linkedin_url"], "EMAIL": PRACTICE["email"], "PHONE": PRACTICE["phone"],
             "PHONE_HREF": PRACTICE["phone_href"].lstrip("+"), "FAX": PRACTICE["fax"], "LOCATION": PRACTICE["location"],
             "STATES": PRACTICE["clinical_states"], "PORTAL_URL": PRACTICE.get("portal_url", "")}
    html = html.replace("{{REGION_NOTE}}", REGION_NOTE).replace("{{CRISIS_NOTE}}", CRISIS_NOTE)
    for k, v in pairs.items():
        html = html.replace("{{" + k + "}}", v)
    assert "{{" not in html, "unreplaced placeholder"
    return html


def contact_block(default=None):
    """Shared contact form (site_src/_contact.html); `default` preselects the 'I am a...' option."""
    html = (SRC / "_contact.html").read_text(encoding="utf-8")
    if default:
        html = html.replace(f'<option value="{default}">', f'<option value="{default}" selected>')
    return html


def page_ld(p, url):
    crumbs = [{"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
              {"@type": "ListItem", "position": 2, "name": p["crumb"], "item": url}]
    return {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": url + "#webpage", "url": url, "name": p["title"], "description": p["desc"],
         "isPartOf": {"@type": "WebSite", "name": "Anavah Institute", "url": BASE + "/"},
         "about": {"@type": "MedicalBusiness", "name": "Anavah Institute", "url": BASE + "/"}},
        {"@type": "BreadcrumbList", "itemListElement": crumbs}]}


def render(p):
    body = p["html"] if p.get("html") else (SRC / f"{p['body']}.body.html").read_text(encoding="utf-8")
    if p["body"] == "index":
        body = body.replace("<!--WHEEL-->", wheel())
    body = re.sub(r"<!--CONTACT(?::([^>]*?))?-->", lambda m: contact_block(m.group(1)), body)
    portal = PRACTICE.get("portal_url", "")
    body = re.sub(r"<!--PORTAL-->(.*?)<!--/PORTAL-->", (lambda m: m.group(1)) if portal else "", body, flags=re.S)
    url = BASE + (p["path"] if p["path"] != "/404" else "/")
    robots = "index,follow,max-image-preview:large" if p["index"] else "noindex,nofollow"
    ld_obj = JSONLD if p.get("ld") else (page_ld(p, url) if p.get("crumb") and p["index"] else None)
    ld = f'<script type="application/ld+json">{json.dumps(ld_obj)}</script>' if ld_obj else ""
    nav = re.sub(r' data-p="([^"]*)"', lambda m: ' aria-current="page"' if m.group(1) == p["path"] else "", NAV)
    scripts = "\n".join(f'<script src="/assets/{s}" defer></script>' for s in p["scripts"] + ["mia.js"])
    return subst(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(p['title'])}</title>
<meta name="description" content="{esc(p['desc'])}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Anavah Institute">
<meta property="og:title" content="{esc(p['title'])}"><meta property="og:description" content="{esc(p['desc'])}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}/assets/img/hero-clouds.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0F1E3A">
<link rel="icon" href="/assets/img/logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,400;1,500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
<link rel="stylesheet" href="/assets/app.css">
{ld}
</head>
<body>
{nav}
{body}
{FOOTER}
{scripts}
</body>
</html>
""")


def main():
    OUT.mkdir(exist_ok=True)
    for p in PAGES:
        (OUT / p["file"]).write_text(render(p), encoding="utf-8")
    urls = [BASE + p["path"] for p in PAGES if p["index"]]
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls) + "\n</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nDisallow: /manage\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    print("built", [p["file"] for p in PAGES])


if __name__ == "__main__":
    main()
