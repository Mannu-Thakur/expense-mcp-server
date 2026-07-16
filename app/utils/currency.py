SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "SGD"}


def is_valid_currency(code: str) -> bool:
    """Return True if the currency code is supported."""
    return code.upper() in SUPPORTED_CURRENCIES


def normalize_currency(code: str) -> str:
    """Return upper-cased currency code, defaulting to INR."""
    return code.upper() if code else "INR"
