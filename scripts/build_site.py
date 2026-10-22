"""Generates site/*.html from site_src/*.body.html with a shared head, nav, footer, and Mia widget.

Usage: python scripts/build_site.py [https://your-domain]
Output is committed, so Render does not need to run this.
"""
import json
import math
import sys
from pathlib import Path

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
    "faxNumber": "+1-216-625-0053",
    "email": PRACTICE["email"],
    "sameAs": [PRACTICE["linkedin_url"], PRACTICE["headway_url"], PRACTICE["skool_url"]],
    "address": {"@type": "PostalAddress", "addressLocality": "New York", "addressRegion": "NY", "addressCountry": "US"},
    "areaServed": [{"@type": "State", "name": "New York"}, {"@type": "State", "name": "Ohio"}],
    "medicalSpecialty": "Psychiatric",
    "founder": {"@type": "Person", "name": "Phillip Scherbakov", "jobTitle": "Psychiatric Nurse Practitioner (PMHNP)"},
    "potentialAction": {"@type": "ReserveAction", "target": PRACTICE["booking_url"], "name": "Schedule a Consultation"},
}

NAV = """<a class="skip" href="#main">Skip to content</a>
<nav class="site-nav" id="nav">
  <div class="container nav-inner">
    <a href="/" class="site-logo"><span class="logo-mark"></span>Anavah<span class="tag">Institute</span></a>
    <ul class="nav-menu" id="navMenu">
      <li><a href="/#appointments">Patients</a></li>
      <li><a href="/#services">Professionals</a></li>
      <li><a href="/#about">About</a></li>
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
      <div class="footer-col"><h6>Patients</h6><ul><li><a href="/#appointments">Appointments</a></li><li><a href="/#services">Our Services</a></li><li><a href="{{BOOKING_URL}}" target="_blank" rel="noopener">Schedule a Consultation</a></li><li><a href="{{HEADWAY_URL}}" target="_blank" rel="noopener">Headway profile</a></li><li><a href="{{SKOOL_URL}}" target="_blank" rel="noopener">Community</a></li></ul></div>
      <div class="footer-col"><h6>Clinicians</h6><ul><li><a href="/#services">Connecting Clinicians</a></li><li><a href="/#appointments">Lunch and Learns</a></li><li><a href="{{BOOKING_URL}}" target="_blank" rel="noopener">Consultation Calls</a></li><li><a href="{{SKOOL_URL}}" target="_blank" rel="noopener">Clinician community</a></li></ul></div>
      <div class="footer-col"><h6>Institute</h6><ul><li><a href="/#about">About Phillip</a></li><li><a href="/#contact">Contact</a></li><li><a href="{{LINKEDIN_URL}}" target="_blank" rel="noopener">LinkedIn</a></li><li><a href="/terms">Terms and Conditions</a></li><li><a href="/privacy">Privacy Policy</a></li></ul></div>
    </div>
    <div class="footer-bottom">
      <span>Copyright &copy; 2026 Anavah Institute - All Rights Reserved.</span>
      <span>In an emergency call 911 &middot; Crisis support: call or text 988</span>
    </div>
  </div>
</footer>"""

PAGES = [
    dict(file="index.html", path="/", body="index", index=True,
         title="Anavah Institute | Integrative Psychiatry & Care Coordination in Chelsea, Manhattan",
         desc="Anavah Institute, led by Phillip Scherbakov, PMHNP, bridges mental health and physical medicine in Chelsea, Manhattan: psychiatric care, nutrition, exercise screening, integrative blood work and care coordination.",
         scripts=["main.js", "orb.js", "contact.js"], ld=True),
    dict(file="book.html", path="/book", body="book", index=True,
         title="Schedule an Initial Consultation | Anavah Institute",
         desc="Schedule an initial consultation with Anavah Institute. Patients and healthcare providers both start here. Clinical care in Ohio and New York; provider services worldwide.",
         scripts=["main.js"]),
    dict(file="book-internal.html", path="/book-internal", body="book-internal", index=False,
         title="Book an Appointment | Anavah Institute", desc="Book an appointment with Anavah Institute.",
         scripts=["main.js", "booking.js"]),
    dict(file="manage.html", path="/manage", body="manage", index=False,
         title="Manage Your Appointment | Anavah Institute", desc="Change or cancel your Anavah Institute appointment.",
         scripts=["main.js", "booking.js"]),
    dict(file="privacy.html", path="/privacy", body="privacy", index=True,
         title="Privacy Policy | Anavah Institute", desc="How Anavah Institute collects, uses and protects information on this website.",
         scripts=["main.js"]),
    dict(file="terms.html", path="/terms", body="terms", index=True,
         title="Terms and Conditions | Anavah Institute", desc="Terms of use for the Anavah Institute website and online booking.",
         scripts=["main.js"]),
    dict(file="404.html", path="/404", body="404", index=False,
         title="Page not found | Anavah Institute", desc="Page not found.", scripts=["main.js"]),
]


def subst(html):
    pairs = {"BOOKING_URL": PRACTICE["booking_url"], "HEADWAY_URL": PRACTICE["headway_url"], "SKOOL_URL": PRACTICE["skool_url"],
             "LINKEDIN_URL": PRACTICE["linkedin_url"], "EMAIL": PRACTICE["email"], "PHONE": PRACTICE["phone"],
             "PHONE_HREF": PRACTICE["phone_href"].lstrip("+"), "FAX": PRACTICE["fax"], "LOCATION": PRACTICE["location"],
             "STATES": PRACTICE["clinical_states"]}
    for k, v in pairs.items():
        html = html.replace("{{" + k + "}}", v)
    assert "{{" not in html, "unreplaced placeholder"
    return html


def render(p):
    body = (SRC / f"{p['body']}.body.html").read_text()
    if p["body"] == "index":
        body = body.replace("<!--WHEEL-->", wheel())
    url = BASE + (p["path"] if p["path"] != "/404" else "/")
    robots = "index,follow,max-image-preview:large" if p["index"] else "noindex,nofollow"
    ld = f'<script type="application/ld+json">{json.dumps(JSONLD)}</script>' if p.get("ld") else ""
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
{NAV}
{body}
{FOOTER}
{scripts}
</body>
</html>
""")


def main():
    OUT.mkdir(exist_ok=True)
    for p in PAGES:
        (OUT / p["file"]).write_text(render(p))
    urls = [BASE + "/", BASE + "/book", BASE + "/privacy", BASE + "/terms"]  # /book = consultation page
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls) + "\n</urlset>\n")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nDisallow: /manage\nSitemap: {BASE}/sitemap.xml\n")
    print("built", [p["file"] for p in PAGES])


if __name__ == "__main__":
    main()
