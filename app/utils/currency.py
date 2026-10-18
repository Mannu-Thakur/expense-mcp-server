from decimal import Decimal, InvalidOperation

SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "SGD"}
CURRENCY_FRACTION_DIGITS = {
    "INR": 2,
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "JPY": 0,
    "AUD": 2,
    "CAD": 2,
    "SGD": 2,
}


def is_valid_currency(code: str) -> bool:
    return isinstance(code, str) and code.strip().upper() in SUPPORTED_CURRENCIES


def normalize_currency(code: str | None) -> str:
    return code.strip().upper() if code is not None else "INR"


def validate_amount_currency(amount: Decimal, currency: str) -> None:
    if not is_valid_currency(currency):
        raise ValueError("Currency must be one of INR, USD, EUR, GBP, JPY, AUD, CAD, or SGD.")
    try:
        precision = CURRENCY_FRACTION_DIGITS[currency]
        quantum = Decimal(1).scaleb(-precision)
        if amount != amount.quantize(quantum):
            raise ValueError(f"{currency} amounts support at most {precision} fractional digits.")
    except (InvalidOperation, KeyError) as exc:
        raise ValueError("Amount cannot be represented in the selected currency.") from exc