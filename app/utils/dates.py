from datetime import date, datetime, timezone


def today_iso() -> str:
    """Return the current UTC date as an ISO-8601 string."""
    return today_utc().isoformat()


def today_utc() -> date:
    """Return the current UTC calendar date."""
    return datetime.now(timezone.utc).date()


def parse_date(value: str) -> date:
    """Parse an ISO-8601 date string, raise ValueError on bad input."""
    return date.fromisoformat(value)
