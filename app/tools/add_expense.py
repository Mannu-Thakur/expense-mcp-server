from datetime import date
from decimal import Decimal

from app.auth import get_request_owner_id, require_write_scope
from app.mcp_instance import mcp
from app.schemas.expense import ExpenseCreate
from app.services.expense_service import ExpenseService
from app.utils.dates import today_utc


@mcp.tool()
def add_expense(
    amount: Decimal,
    category: str,
    description: str = "",
    merchant: str = "",
    payment_method: str = "Cash",
    currency: str = "INR",
    expense_date: str = "",
) -> dict:
    """Add a new expense. HTTP callers need expenses:write."""
    require_write_scope()
    parsed_date = date.fromisoformat(expense_date) if expense_date else today_utc()
    expense = ExpenseCreate(
        amount=amount,
        category=category,
        description=description or None,
        merchant=merchant or None,
        payment_method=payment_method or None,
        currency=currency,
        expense_date=parsed_date,
    )
    saved = ExpenseService.add_expense(expense, owner_id=get_request_owner_id())
    return {
        "message": "Expense added successfully.",
        "expense_id": saved.id,
        "amount": float(saved.amount),
        "category": saved.category,
        "merchant": saved.merchant,
        "currency": saved.currency,
        "expense_date": str(saved.expense_date),
    }