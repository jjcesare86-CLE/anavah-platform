from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import db, scheduling
from .config import ROOT, settings
from .routes import admin, agent, public

SITE = ROOT / "site"
ADMIN = ROOT / "admin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_sqlite_if_needed()
    try:
        with db.get_engine().begin() as conn:
            scheduling.seed_defaults(conn)
    except Exception as e:  # schema not applied yet: keep the site up, log loudly
        print(f"[startup] seed skipped: {e!r} — did you run supabase/schema.sql?")
    yield


app = FastAPI(title="Anavah Platform", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.middleware("http")
async def headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "microphone=(self), geolocation=(), camera=()")
    resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith("/admin") or request.url.path.startswith("/api/"):
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


@app.get("/healthz")
def healthz():
    return {"ok": True}


app.include_router(public.router)
app.include_router(agent.router)
app.include_router(admin.router)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": getattr(exc, "detail", "Not found")}, status_code=404)
    return FileResponse(SITE / "404.html", status_code=404)


PAGES = {"/": "index.html", "/privacy": "privacy.html", "/terms": "terms.html"}


def _page(name: str):
    def handler():
        return FileResponse(SITE / name)
    return handler


for path, fname in PAGES.items():
    app.add_api_route(path, _page(fname), methods=["GET"], include_in_schema=False)


@app.get("/book", include_in_schema=False)
def book_page():
    # Default: the consultation page that links to Google Calendar. BOOKING_MODE=internal serves the built-in calendar.
    return FileResponse(SITE / ("book-internal.html" if settings.booking_mode == "internal" else "book.html"))


@app.get("/manage", include_in_schema=False)
def manage_page():
    if settings.booking_mode != "internal":
        return RedirectResponse("/book", status_code=302)
    return FileResponse(SITE / "manage.html")


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return FileResponse(SITE / "robots.txt", media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    return FileResponse(SITE / "sitemap.xml", media_type="application/xml")


@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
def admin_page():
    return FileResponse(ADMIN / "index.html", headers={"X-Robots-Tag": "noindex, nofollow"})


app.mount("/admin/static", StaticFiles(directory=ADMIN), name="admin-static")
app.mount("/assets", StaticFiles(directory=SITE / "assets"), name="assets")
