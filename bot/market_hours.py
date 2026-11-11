"""Market-open logic per location. Holidays are not handled yet (TODO)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .config import Location


def is_open(loc: Location, now: datetime | None = None) -> bool:
    now = (now or datetime.now(timezone.utc)).astimezone(loc.tz)
    if now.weekday() not in loc.weekdays:
        return False
    return loc.open <= now.time() < loc.close


def next_open(loc: Location, now: datetime | None = None) -> datetime:
    """Next opening time (tz-aware, in the location's timezone) strictly after now."""
    now = (now or datetime.now(timezone.utc)).astimezone(loc.tz)
    for days in range(0, 8):
        day = (now + timedelta(days=days)).date()
        candidate = datetime.combine(day, loc.open, tzinfo=loc.tz)
        if candidate.weekday() in loc.weekdays and candidate > now:
            return candidate
    raise RuntimeError(f"No trading day configured for {loc.code}")


def minutes_since_open(loc: Location, now: datetime | None = None) -> float | None:
    now = (now or datetime.now(timezone.utc)).astimezone(loc.tz)
    if not is_open(loc, now):
        return None
    opened = datetime.combine(now.date(), loc.open, tzinfo=loc.tz)
    return (now - opened).total_seconds() / 60
