from datetime import date


def today_iso() -> str:
    """Return today's date as an ISO-8601 string."""
    return date.today().isoformat()


def parse_date(value: str) -> date:
    """Parse an ISO-8601 date string, raise ValueError on bad input."""
    return date.fromisoformat(value)
