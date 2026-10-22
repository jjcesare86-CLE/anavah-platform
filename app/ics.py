from datetime import datetime, timezone

from .config import PRACTICE, settings


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def appointment_ics(appt: dict) -> str:
    where = "Telehealth (link provided by the office)" if appt["mode"] == "telehealth" else PRACTICE["location"]
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Anavah Institute//Booking//EN", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH", "BEGIN:VEVENT",
        f"UID:{appt['id']}@anavah-institute.org",
        f"DTSTAMP:{_fmt(datetime.now(timezone.utc))}",
        f"DTSTART:{_fmt(appt['start_at'])}", f"DTEND:{_fmt(appt['end_at'])}",
        f"SUMMARY:{_esc(appt['type_name'] + ' - ' + PRACTICE['name'])}",
        f"LOCATION:{_esc(where)}",
        f"DESCRIPTION:{_esc('Manage or cancel: ' + settings.site_url + '/manage?t=' + appt['manage_token'])}",
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"
