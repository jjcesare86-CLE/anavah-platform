"""SQLAlchemy Core tables (mirror of supabase/schema.sql) and engine helpers.

Production uses Postgres from supabase/schema.sql (incl. the overlap exclusion constraint).
Tests/local dev use SQLite via metadata.create_all(); the app also checks overlaps in code.
"""
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from .config import settings

metadata = sa.MetaData()


def _id():
    return sa.Column("id", sa.Uuid, primary_key=True, default=uuid.uuid4)


def _now():
    return datetime.now(timezone.utc)


TS = sa.DateTime(timezone=True)

clients = sa.Table(
    "clients", metadata, _id(),
    sa.Column("first_name", sa.Text, nullable=False, default=""),
    sa.Column("last_name", sa.Text, nullable=False, default=""),
    sa.Column("email", sa.Text), sa.Column("phone", sa.Text),
    sa.Column("status", sa.Text, nullable=False, default="lead"),
    sa.Column("source", sa.Text, nullable=False, default="manual"),
    sa.Column("tags", sa.JSON, nullable=False, default=list),
    sa.Column("notes", sa.Text, nullable=False, default=""),
    sa.Column("email_consent", sa.Boolean, nullable=False, default=False),
    sa.Column("sms_consent", sa.Boolean, nullable=False, default=False),
    sa.Column("do_not_contact", sa.Boolean, nullable=False, default=False),
    sa.Column("ghl_contact_id", sa.Text),
    sa.Column("created_at", TS, nullable=False, default=_now),
    sa.Column("updated_at", TS, nullable=False, default=_now),
)

client_notes = sa.Table(
    "client_notes", metadata, _id(),
    sa.Column("client_id", sa.Uuid, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
    sa.Column("body", sa.Text, nullable=False),
    sa.Column("created_by", sa.Text),
    sa.Column("created_at", TS, nullable=False, default=_now),
)

appointment_types = sa.Table(
    "appointment_types", metadata, _id(),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("slug", sa.Text, nullable=False, unique=True),
    sa.Column("description", sa.Text, nullable=False, default=""),
    sa.Column("audience", sa.Text, nullable=False, default="patient"),
    sa.Column("duration_min", sa.Integer, nullable=False, default=30),
    sa.Column("buffer_after_min", sa.Integer, nullable=False, default=0),
    sa.Column("mode", sa.Text, nullable=False, default="either"),
    sa.Column("active", sa.Boolean, nullable=False, default=True),
    sa.Column("sort", sa.Integer, nullable=False, default=0),
)

availability_rules = sa.Table(
    "availability_rules", metadata, _id(),
    sa.Column("weekday", sa.Integer, nullable=False),
    sa.Column("start_time", sa.Text, nullable=False),
    sa.Column("end_time", sa.Text, nullable=False),
    sa.Column("active", sa.Boolean, nullable=False, default=True),
)

time_off = sa.Table(
    "time_off", metadata, _id(),
    sa.Column("start_at", TS, nullable=False),
    sa.Column("end_at", TS, nullable=False),
    sa.Column("reason", sa.Text, nullable=False, default=""),
)

appointments = sa.Table(
    "appointments", metadata, _id(),
    sa.Column("client_id", sa.Uuid, sa.ForeignKey("clients.id"), nullable=False),
    sa.Column("type_id", sa.Uuid, sa.ForeignKey("appointment_types.id", ondelete="SET NULL")),
    sa.Column("type_name", sa.Text, nullable=False, default=""),
    sa.Column("start_at", TS, nullable=False),
    sa.Column("end_at", TS, nullable=False),
    sa.Column("blocked_until", TS, nullable=False),
    sa.Column("status", sa.Text, nullable=False, default="confirmed"),
    sa.Column("mode", sa.Text, nullable=False, default="telehealth"),
    sa.Column("notes", sa.Text, nullable=False, default=""),
    sa.Column("client_message", sa.Text, nullable=False, default=""),
    sa.Column("manage_token", sa.Text, nullable=False, unique=True),
    sa.Column("source", sa.Text, nullable=False, default="web"),
    sa.Column("reminder_sent_at", TS),
    sa.Column("cancelled_at", TS),
    sa.Column("created_at", TS, nullable=False, default=_now),
)

prospects = sa.Table(
    "prospects", metadata, _id(),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("organization", sa.Text, nullable=False, default=""),
    sa.Column("role", sa.Text, nullable=False, default=""),
    sa.Column("category", sa.Text, nullable=False, default="provider"),
    sa.Column("email", sa.Text), sa.Column("phone", sa.Text),
    sa.Column("status", sa.Text, nullable=False, default="new"),
    sa.Column("notes", sa.Text, nullable=False, default=""),
    sa.Column("do_not_contact", sa.Boolean, nullable=False, default=False),
    sa.Column("ghl_contact_id", sa.Text),
    sa.Column("created_at", TS, nullable=False, default=_now),
    sa.Column("updated_at", TS, nullable=False, default=_now),
)

templates = sa.Table(
    "templates", metadata, _id(),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("channel", sa.Text, nullable=False),
    sa.Column("subject", sa.Text, nullable=False, default=""),
    sa.Column("body", sa.Text, nullable=False),
    sa.Column("created_at", TS, nullable=False, default=_now),
)

messages = sa.Table(
    "messages", metadata, _id(),
    sa.Column("client_id", sa.Uuid, sa.ForeignKey("clients.id", ondelete="SET NULL")),
    sa.Column("prospect_id", sa.Uuid, sa.ForeignKey("prospects.id", ondelete="SET NULL")),
    sa.Column("appointment_id", sa.Uuid, sa.ForeignKey("appointments.id", ondelete="SET NULL")),
    sa.Column("channel", sa.Text, nullable=False),
    sa.Column("kind", sa.Text, nullable=False, default="outreach"),
    sa.Column("to_address", sa.Text, nullable=False, default=""),
    sa.Column("subject", sa.Text, nullable=False, default=""),
    sa.Column("body", sa.Text, nullable=False, default=""),
    sa.Column("status", sa.Text, nullable=False, default="queued"),
    sa.Column("error", sa.Text, nullable=False, default=""),
    sa.Column("provider_id", sa.Text),
    sa.Column("created_at", TS, nullable=False, default=_now),
)

unsubscribes = sa.Table(
    "unsubscribes", metadata,
    sa.Column("address", sa.Text, primary_key=True),
    sa.Column("channel", sa.Text, nullable=False),
    sa.Column("created_at", TS, nullable=False, default=_now),
)

settings_table = sa.Table(
    "settings", metadata,
    sa.Column("key", sa.Text, primary_key=True),
    sa.Column("value", sa.JSON, nullable=False),
)

_engine: Engine | None = None


def _normalize(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = _normalize(settings.database_url)
        if url.startswith("sqlite"):
            _engine = sa.create_engine(url, connect_args={"check_same_thread": False})
        else:
            # prepare_threshold=None: required for Supabase's pooled connections
            _engine = sa.create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5,
                                       connect_args={"prepare_threshold": None})
    return _engine


def reset_engine():
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def init_sqlite_if_needed():
    """For local dev/tests only. Postgres schema comes from supabase/schema.sql."""
    eng = get_engine()
    if eng.dialect.name == "sqlite":
        metadata.create_all(eng)


def utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; normalise everything to aware UTC."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def row(r) -> dict:
    d = dict(r._mapping)
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = utc(v)
    return d
