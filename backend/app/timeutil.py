"""All times are server-side UTC; the frontend displays IST."""

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def days_between(later: datetime, earlier: datetime) -> float:
    return (later - earlier).total_seconds() / 86400


def mmss_to_sec(value: str | None) -> float | None:
    if not value:
        return None
    try:
        parts = [float(p) for p in str(value).strip().split(":")]
    except ValueError:
        return None
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def sec_to_mmss(sec: float) -> str:
    sec = max(0, int(round(sec)))
    return f"{sec // 60:02d}:{sec % 60:02d}"
